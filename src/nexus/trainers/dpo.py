"""
dpo.py — Direct Preference Optimization (DPO) trainer.

What is DPO?
────────────
DPO (Rafailov et al., 2023) is a preference-tuning algorithm.

The classic way to align LLMs with human preferences is RLHF (Reinforcement
Learning from Human Feedback), which requires training a separate reward model
and then running PPO optimisation — complex and computationally expensive.

DPO simplifies this dramatically: it directly optimises the model to prefer
"chosen" responses over "rejected" responses using a binary cross-entropy loss.

The math (don't worry if it's fuzzy at first):
  DPO reformulates RLHF as a classification problem. Given a prompt x and
  two responses (y_w = chosen, y_l = rejected), it maximises:

    log σ( β · log[π(y_w|x) / π_ref(y_w|x)]
           − β · log[π(y_l|x) / π_ref(y_l|x)] )

  where:
    π     = the model being trained
    π_ref = a frozen copy of the model before training ("reference model")
    β     = temperature controlling how far we deviate from the reference

  In English: increase the probability of chosen responses relative to the
  reference model, and decrease the probability of rejected responses.

Data format:
  Each training example needs three things:
    prompt:   the input question or instruction
    chosen:   the better response (e.g. more helpful, more accurate)
    rejected: the worse response (e.g. unhelpful, harmful, wrong)

When to use DPO vs SFT:
  SFT → teaches the model WHAT to say
  DPO → teaches the model to prefer better responses over worse ones
  Typical workflow: SFT first, then DPO to refine quality
"""

from __future__ import annotations

import logging

from trl import DPOConfig, DPOTrainer

from nexus.config import Recipe
from nexus.data.formatters import prepare_dpo_dataset
from nexus.data.loaders import load_and_split
from nexus.models.adapters import apply_lora, merge_and_save
from nexus.models.loader import load_model, load_tokenizer
from nexus.models.policy import write_model_manifest

logger = logging.getLogger(__name__)


def run_dpo(recipe: Recipe) -> None:
    """Run a full DPO training run from a Recipe.

    DPO requires a reference model (frozen copy of the initial model).
    TRL's DPOTrainer handles this automatically — it keeps a copy of the
    model at initialisation and uses it to compute the reference log-probs.

    Args:
        recipe: a fully validated Recipe loaded from a YAML config
    """
    logger.info(f"Starting DPO run: {recipe.name}")

    # ── 1. Load tokenizer + model ─────────────────────────────────────────
    tokenizer = load_tokenizer(recipe.model)
    model = load_model(recipe.model)

    # ── 2. Apply LoRA ─────────────────────────────────────────────────────
    # With DPO + LoRA, the reference model is implicitly the base model
    # (before adapters are applied), which saves memory vs. keeping a full copy.
    if recipe.lora is not None:
        model = apply_lora(model, recipe.lora)

    # ── 3. Load dataset ────────────────────────────────────────────────────
    splits = load_and_split(recipe.data)
    train_dataset = prepare_dpo_dataset(splits["train"], recipe.data.dataset_name)
    eval_dataset = prepare_dpo_dataset(splits["validation"], recipe.data.dataset_name)

    # ── 4. Configure DPO ──────────────────────────────────────────────────
    t = recipe.training
    output_dir = str(recipe.resolve_output_dir())

    dpo_config = DPOConfig(
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
        # DPO-specific hyperparameters
        beta=0.1,  # KL penalty — how far to allow deviating from reference
        # higher β → stays closer to reference model
        # lower β → more aggressive preference optimisation
        max_length=recipe.model.max_seq_len,
        truncation_mode="keep_end",
    )

    # ── 5. Train ───────────────────────────────────────────────────────────
    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # None = use the frozen base model as reference (memory efficient)
        args=dpo_config,
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
