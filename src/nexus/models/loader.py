"""
loader.py — Load Gemma models and tokenizers correctly on Apple Silicon.

What happens when you "load a model"?
──────────────────────────────────────
A language model is a large neural network stored as a file of numbers
(weights) on HuggingFace. Loading a model means:
  1. Download the weight files (first time only, cached after)
  2. Build the network architecture in Python
  3. Copy the weights into memory on your device (MPS or CPU)

The tokenizer is a separate component that converts text ↔ token IDs.
Tokens are the basic units the model operates on — roughly, word pieces.
For example, "hello" might be one token, "posttraining" might be two.

Gemma vocabulary size is much larger than GPT-2's 50,257 tokens.

Why "-it" models?
─────────────────
HuggingFace hosts base and instruction-tuned variants of Gemma models.

For posttraining experiments we almost always start from the -it model because:
  - It already understands the chat format
  - It already knows how to follow instructions
  - We're teaching it *new skills*, not basic behaviour

Starting from the base model is called "pretraining" or "continued pretraining".
"""

from __future__ import annotations

import logging

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizer

from nexus.config import ModelConfig
from nexus.device import get_device, get_dtype

logger = logging.getLogger(__name__)


def load_tokenizer(cfg: ModelConfig) -> PreTrainedTokenizer:
    """Load the tokenizer for the specified model.

    The tokenizer converts text → token IDs and back.
    We set pad_token = eos_token because Gemma doesn't have a dedicated
    padding token — using the end-of-sequence token for padding is standard.

    padding_side="right" ensures padding tokens are appended at the end
    of the sequence (left padding can confuse causal language models).
    """
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_id)

    # Gemma has no pad token by default — set it to eos
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Right-pad for causal LM training (attention mask is applied left→right)
    tokenizer.padding_side = "right"

    logger.info(f"Tokenizer loaded: vocab_size={tokenizer.vocab_size}")
    return tokenizer


def load_model(cfg: ModelConfig) -> AutoModelForCausalLM:
    """Load a Gemma model with correct precision for Apple Silicon.

    Key decisions:
    ──────────────
    dtype=bfloat16
        Halves memory usage. Gemma was trained in bfloat16 so this is safe.
        Never use float16 with Gemma — it causes gradient overflow.

    device_map="auto"
        Lets `accelerate` distribute the model across available devices.
        On a Mac this means MPS (GPU) + CPU if the model is too big for GPU RAM.
        For smaller Gemma-class models it can fit entirely on MPS.

    attn_implementation="eager"
        Flash Attention 2 requires CUDA, so we use the standard attention.
        On Apple Silicon, "sdpa" (scaled dot-product attention) is also good.
    """
    dtype = get_dtype()

    logger.info(f"Loading model: {cfg.model_id}")
    logger.info(f"  dtype={dtype}, device={get_device()}, attn={cfg.attn_implementation}")

    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_id,
        dtype=dtype,
        device_map="auto",  # let accelerate choose device placement
        attn_implementation=cfg.attn_implementation,
    )

    # Log the number of trainable parameters so you know what you're working with
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(
        f"  Parameters: {total_params / 1e6:.0f}M total, {trainable_params / 1e6:.0f}M trainable"
    )

    return model


def count_parameters(model: torch.nn.Module) -> dict[str, int]:
    """Count total and trainable parameters in a model.

    After applying LoRA, call this to confirm that only the adapter
    parameters are trainable (should be ~0.1-1% of total parameters).
    """
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return {
        "total": total,
        "trainable": trainable,
        "frozen": total - trainable,
        "trainable_pct": round(100 * trainable / total, 4) if total > 0 else 0.0,
    }
