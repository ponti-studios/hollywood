"""
base.py — Shared TrainingArguments builder for all TRL trainers.

What are TrainingArguments?
───────────────────────────
The HuggingFace `TrainingArguments` dataclass holds all the hyperparameters
that control the training loop:
  - how many epochs / steps to run
  - what learning rate to use and how to schedule it
  - how often to log / evaluate / save
  - where to save checkpoints
  - which device and precision to use

Building TrainingArguments correctly for Apple Silicon requires a few
non-obvious settings, centralised here so every trainer gets them right.
"""

from __future__ import annotations

from transformers import TrainingArguments

from nexus.config import Recipe


def build_training_args(recipe: Recipe) -> TrainingArguments:
    """Build TrainingArguments from a Recipe config.

    Apple Silicon–specific settings
    ────────────────────────────────
    bf16=True, fp16=False
        Gemma 3 requires bfloat16. MPS supports bfloat16 on M1 Pro/Max/Ultra
        and all M2+ chips. Never use fp16 with Gemma 3.

    optim="adamw_torch"
        The standard AdamW optimiser.
        "adamw_bnb_8bit" (8-bit Adam) is popular on CUDA for memory savings
        but requires bitsandbytes which is CUDA-only.

    dataloader_pin_memory=False
        Pin memory is a CUDA optimisation that pre-loads data into GPU-accessible
        RAM. It has no benefit (and can cause errors) on MPS.

    no_cuda=True
        Explicitly tells the trainer not to try CUDA. Redundant on Mac but safe.
    """
    t = recipe.training
    output_dir = str(recipe.resolve_output_dir())

    return TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=t.num_epochs,
        per_device_train_batch_size=t.batch_size,
        per_device_eval_batch_size=t.batch_size,
        gradient_accumulation_steps=t.gradient_accumulation_steps,
        learning_rate=t.learning_rate,
        weight_decay=t.weight_decay,
        warmup_ratio=t.warmup_ratio,
        lr_scheduler_type="cosine",          # cosine decay is standard for LLM fine-tuning
        max_grad_norm=t.max_grad_norm,
        bf16=t.bf16,
        fp16=False,                          # never fp16 with Gemma 3
        # --- Logging ---
        logging_dir=f"{output_dir}/logs",
        logging_steps=t.logging_steps,
        report_to="wandb" if recipe.wandb.enabled else "none",
        run_name=recipe.wandb.run_name or recipe.name,
        # --- Evaluation & saving ---
        eval_strategy="steps",
        eval_steps=t.eval_steps,
        save_strategy="steps",
        save_steps=t.save_steps,
        save_total_limit=3,                  # keep only the 3 most recent checkpoints
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,             # lower eval loss = better
        # --- Apple Silicon specific ---
        optim="adamw_torch",
        dataloader_pin_memory=False,         # pin_memory is CUDA-only
        use_cpu=False,                       # use MPS not CPU
        # --- Reproducibility ---
        seed=recipe.data.seed,
        data_seed=recipe.data.seed,
    )
