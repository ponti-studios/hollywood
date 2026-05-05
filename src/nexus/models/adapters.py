"""
adapters.py — Create, apply, merge, and save LoRA adapters.

LoRA in plain English
──────────────────────
Imagine the model has a weight matrix W (e.g. 4096 × 4096 = 16M numbers).
Full fine-tuning would update all 16M numbers — expensive.

LoRA instead inserts two small matrices A and B alongside W:
  - A is  (4096 × rank), e.g. rank=16 → 65,536 numbers
  - B is  (rank × 4096), e.g. rank=16 → 65,536 numbers

The effective weight becomes:  W + (B @ A) × (alpha / rank)

During training only A and B are updated. W stays frozen.
During inference you can "merge" A and B back into W (zero overhead).

Why does this work? The hypothesis is that the weight updates needed for
fine-tuning have low intrinsic rank — i.e., the important changes can be
expressed as a product of two small matrices.

This is now the standard approach for fine-tuning LLMs at small scale.
"""

from __future__ import annotations

import logging
from pathlib import Path

from peft import LoraConfig as PeftLoraConfig
from peft import PeftModel, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, PreTrainedTokenizer

from nexus.config import LoraConfig

logger = logging.getLogger(__name__)


def apply_lora(
    model: AutoModelForCausalLM,
    lora_cfg: LoraConfig,
) -> PeftModel:
    """Wrap a model with LoRA adapters and freeze all base model weights.

    After this call:
      - model.parameters() with requires_grad=True  → only LoRA matrices A, B
      - model.parameters() with requires_grad=False → all original weights

    Args:
        model: the loaded base model (from models/loader.py)
        lora_cfg: LoRA hyperparameters from the recipe YAML

    Returns:
        A PeftModel (thin wrapper around the original model + adapters)
    """
    peft_config = PeftLoraConfig(
        task_type=TaskType.CAUSAL_LM,  # we're fine-tuning a causal language model
        r=lora_cfg.rank,
        lora_alpha=lora_cfg.alpha,
        lora_dropout=lora_cfg.dropout,
        target_modules=lora_cfg.target_modules,
        bias=lora_cfg.bias,
        inference_mode=False,  # we want to train, not just infer
    )

    model = get_peft_model(model, peft_config)

    # Print a summary of what's trainable
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(
        f"LoRA applied: {trainable:,} trainable params "
        f"({100 * trainable / total:.3f}% of {total / 1e6:.0f}M total)"
    )

    return model


def merge_and_save(
    model: PeftModel,
    tokenizer: PreTrainedTokenizer,
    output_dir: str | Path,
) -> None:
    """Merge LoRA weights back into the base model and save to disk.

    Why merge?
    ──────────
    Training produces a small adapter checkpoint (~50 MB for rank=16).
    At inference time you can either:
      (a) Load base model + apply adapter each time (slightly slower start)
      (b) Merge adapters into the base weights once → standard model (faster inference)

    This function does option (b). The merged model is a standard transformers
    model that can be loaded with AutoModelForCausalLM.from_pretrained().

    The merged model is saved in HuggingFace "safetensors" format.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Merging LoRA weights into base model …")

    # merge_and_unload: fuses A@B into W and removes the adapter wrappers
    merged = model.merge_and_unload()

    logger.info(f"Saving merged model to {output_dir}")
    merged.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)

    logger.info(f"Done. Load with: AutoModelForCausalLM.from_pretrained('{output_dir}')")


def save_adapter_only(model: PeftModel, output_dir: str | Path) -> None:
    """Save only the LoRA adapter weights (much smaller than full model).

    Adapter-only saves are useful during training checkpoints because they're
    tiny (~50 MB). You still need the original base model to use them.

    To load:
        model = AutoModelForCausalLM.from_pretrained("google/gemma-4-e2b", ...)
        model = PeftModel.from_pretrained(model, output_dir)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    logger.info(f"Adapter saved to {output_dir}")


def load_adapter(
    base_model: AutoModelForCausalLM,
    adapter_dir: str | Path,
) -> PeftModel:
    """Load a previously saved LoRA adapter onto a base model."""
    return PeftModel.from_pretrained(base_model, str(adapter_dir))
