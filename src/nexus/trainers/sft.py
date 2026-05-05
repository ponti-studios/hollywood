"""
sft.py — Supervised Fine-Tuning (SFT) trainer.

What is SFT?
────────────
SFT is the simplest and most common form of LLM fine-tuning.
You provide (prompt, response) pairs and train the model to produce
those responses given those prompts.

The training signal: "predict the next token"
─────────────────────────────────────────────
The model sees the full conversation (prompt + response) as a sequence
of tokens. It's trained to predict each token given all previous tokens.
The loss is only computed on the response tokens — not the prompt tokens.
This is called "response-only" masking.

Why start with SFT?
───────────────────
SFT is the foundation. Before you can do DPO or ORPO, you typically need
a model that can already generate reasonable responses (via SFT).
The progression is usually: SFT → preference tuning (DPO / ORPO).

What SFTTrainer does for you:
  - Handles tokenisation and padding
  - Applies response-only masking automatically
  - Integrates with W&B logging
  - Saves checkpoints and the best model
"""

from __future__ import annotations

import logging

from trl import SFTConfig, SFTTrainer

from nexus.config import Recipe
from nexus.data.formatters import prepare_sft_dataset
from nexus.data.loaders import load_and_split
from nexus.models.adapters import apply_lora
from nexus.models.loader import load_model, load_tokenizer

logger = logging.getLogger(__name__)


def run_sft(recipe: Recipe) -> None:
    """Run a full SFT training run from a Recipe.

    Steps:
      1. Load tokenizer and model
      2. Apply LoRA if configured
      3. Load and format dataset
      4. Initialise SFTTrainer
      5. Train
      6. Save checkpoint

    Args:
        recipe: a fully validated Recipe loaded from a YAML config
    """
    logger.info(f"Starting SFT run: {recipe.name}")

    # ── 1. Load tokenizer + model ─────────────────────────────────────────
    tokenizer = load_tokenizer(recipe.model)
    model = load_model(recipe.model)

    # ── 2. Apply LoRA (if configured) ─────────────────────────────────────
    if recipe.lora is not None:
        model = apply_lora(model, recipe.lora)
    else:
        logger.warning(
            "No LoRA config found — running full fine-tuning. "
            "This requires much more memory. Consider adding a [lora] section."
        )

    # ── 3. Load and format dataset ─────────────────────────────────────────
    splits = load_and_split(recipe.data)
    train_dataset = prepare_sft_dataset(splits["train"], tokenizer, recipe.data.dataset_name)
    eval_dataset = prepare_sft_dataset(splits["validation"], tokenizer, recipe.data.dataset_name)

    # ── 4. Build training config ───────────────────────────────────────────
    # SFTConfig extends TrainingArguments with SFT-specific options
    t = recipe.training
    output_dir = str(recipe.resolve_output_dir())

    sft_config = SFTConfig(
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
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="wandb" if recipe.wandb.enabled else "none",
        run_name=recipe.wandb.run_name or recipe.name,
        optim="adamw_torch",
        dataloader_pin_memory=False,
        seed=recipe.data.seed,
        # SFT-specific: the column that contains the formatted text
        dataset_text_field="text",
        # Truncate examples longer than max_seq_len
        max_length=recipe.model.max_seq_len,
        # Pack multiple short examples into one sequence for efficiency
        # Disable for simplicity when starting out
        packing=False,
    )

    # ── 5. Initialise and run trainer ─────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    logger.info("Training …")
    trainer.train()

    # ── 6. Save final model ───────────────────────────────────────────────
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"Model saved to {output_dir}")
