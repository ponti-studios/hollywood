"""
orpo.py — Odds Ratio Preference Optimization (ORPO) trainer.

What is ORPO?
─────────────
ORPO (Hong et al., 2024) is a newer preference-tuning algorithm that
combines SFT and preference tuning into a single training pass.

Recall that the typical workflow is:
  Step 1: SFT (teach the model the instruction-following format)
  Step 2: DPO (teach the model to prefer good responses)

ORPO does both simultaneously by adding an "odds ratio" penalty to the
standard SFT loss:

  ORPO loss = SFT loss − λ · log σ(log OR(y_w) − log OR(y_l))

Where the "odds ratio" for a response y given prompt x is:
  OR(y|x) = P(y|x) / (1 − P(y|x))

In English: simultaneously maximise the probability of the chosen response
AND penalise the model for also assigning high probability to the rejected one.

Advantages of ORPO over DPO:
  - No reference model needed → saves memory (important on a Mac)
  - Single training stage instead of two (SFT → DPO)
  - Empirically competitive or better than SFT+DPO on many benchmarks

When to use ORPO:
  When you have preference data (chosen/rejected pairs) and want to fine-tune
  efficiently in a single pass. Good for resource-constrained environments
  like Apple Silicon.
"""

from __future__ import annotations

import logging

from trl.experimental.orpo.orpo_config import ORPOConfig
from trl.experimental.orpo.orpo_trainer import ORPOTrainer

from nexus.config import Recipe
from nexus.data.formatters import prepare_dpo_dataset
from nexus.data.loaders import load_and_split
from nexus.models.adapters import apply_lora, merge_and_save
from nexus.models.loader import load_model, load_tokenizer
from nexus.models.policy import write_model_manifest

logger = logging.getLogger(__name__)


def run_orpo(recipe: Recipe) -> None:
    """Run a full ORPO training run from a Recipe.

    ORPO uses the same (prompt, chosen, rejected) data format as DPO,
    so we reuse prepare_dpo_dataset() here.

    Args:
        recipe: a fully validated Recipe loaded from a YAML config
    """
    logger.info(f"Starting ORPO run: {recipe.name}")

    # ── 1. Load tokenizer + model ─────────────────────────────────────────
    tokenizer = load_tokenizer(recipe.model)
    model = load_model(recipe.model)

    # ── 2. Apply LoRA ─────────────────────────────────────────────────────
    if recipe.lora is not None:
        model = apply_lora(model, recipe.lora)

    # ── 3. Load dataset ────────────────────────────────────────────────────
    # ORPO uses the same (prompt, chosen, rejected) format as DPO
    splits = load_and_split(recipe.data)
    train_dataset = prepare_dpo_dataset(splits["train"], recipe.data.dataset_name)
    eval_dataset = prepare_dpo_dataset(splits["validation"], recipe.data.dataset_name)

    # ── 4. Configure ORPO ─────────────────────────────────────────────────
    t = recipe.training
    output_dir = str(recipe.resolve_output_dir())

    orpo_config = ORPOConfig(
        output_dir=output_dir,
        num_train_epochs=t.num_epochs,
        per_device_train_batch_size=t.batch_size,
        per_device_eval_batch_size=t.batch_size,
        gradient_accumulation_steps=t.gradient_accumulation_steps,
        learning_rate=t.learning_rate,
        weight_decay=t.weight_decay,
        warmup_ratio=t.warmup_ratio,
        lr_scheduler_type="cosine",
        max_grad_norm=t.max_grad_norm,
        bf16=t.bf16,
        fp16=False,
        logging_steps=t.logging_steps,
        eval_strategy="steps",
        eval_steps=t.eval_steps,
        save_strategy="steps",
        save_steps=t.save_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        report_to="wandb" if recipe.wandb.enabled else "none",
        run_name=recipe.wandb.run_name or recipe.name,
        optim="adamw_torch",
        dataloader_pin_memory=False,
        seed=recipe.data.seed,
        # ORPO-specific: the λ (lambda) weight for the odds-ratio penalty term
        # Higher → more aggressive preference tuning, lower → more conservative
        # Paper recommends 0.1; try 0.05–0.5
        beta=0.1,
        max_length=recipe.model.max_seq_len,
        max_completion_length=recipe.model.max_seq_len // 2,
    )

    # ── 5. Train ───────────────────────────────────────────────────────────
    trainer = ORPOTrainer(
        model=model,
        args=orpo_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    logger.info("Training …")
    trainer.train()

    if recipe.lora is not None:
        merge_and_save(model, tokenizer, output_dir)
    else:
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)
        write_model_manifest(output_dir)

    logger.info(f"Model saved to {output_dir}")
