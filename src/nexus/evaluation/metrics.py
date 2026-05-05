"""
metrics.py — Standard evaluation metrics for language model fine-tuning.

Why evaluate?
─────────────
Training loss tells you how well the model fits the training data.
But you care about how well the model performs on NEW data it hasn't seen.
Evaluation metrics measure generalisation.

Key metrics explained
──────────────────────
Perplexity
  Measures how "surprised" the model is by the validation text.
  Lower = better. A perplexity of 10 means the model assigns, on average,
  the same probability as uniformly choosing from 10 options at each step.
  Perplexity = exp(cross_entropy_loss)

  Perplexity values to orient yourself:
    > 100  — model barely learned anything
    10–50  — reasonable language model
    < 10   — very good fit (possibly overfitting if training data was small)

Win rate (for preference tasks)
  After DPO/ORPO training: what fraction of the time does the fine-tuned
  model's response score higher than the base model's? (via LLM-as-judge)
  Win rate > 50% = improvement over base model.

BLEU / ROUGE
  Classic text similarity metrics. Useful sanity checks but not the
  primary signal for modern LLMs — use LLM-as-judge for quality.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, PreTrainedTokenizer

logger = logging.getLogger(__name__)


def compute_perplexity(
    model: AutoModelForCausalLM,
    tokenizer: PreTrainedTokenizer,
    texts: list[str],
    batch_size: int = 4,
    max_length: int = 512,
    device: str = "mps",
) -> float:
    """Compute perplexity of a list of texts under the given model.

    Lower perplexity = the model finds these texts more likely.

    Args:
        model:      loaded language model
        tokenizer:  corresponding tokenizer
        texts:      list of text strings to evaluate
        batch_size: how many texts to process at once
        max_length: truncate texts longer than this
        device:     "mps" or "cpu"

    Returns:
        Average perplexity across all texts.
    """
    model.eval()
    total_loss = 0.0
    total_tokens = 0

    with torch.no_grad():
        for i in tqdm(range(0, len(texts), batch_size), desc="Computing perplexity"):
            batch = texts[i : i + batch_size]
            encodings = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length,
            )
            input_ids = encodings["input_ids"].to(device)
            attention_mask = encodings["attention_mask"].to(device)

            # Labels: same as input_ids but with padding tokens set to -100
            # The model only computes loss on non-padding tokens
            labels = input_ids.clone()
            labels[attention_mask == 0] = -100

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )

            # outputs.loss is the mean cross-entropy over non-padding tokens
            # We weight by the number of non-padding tokens to get a proper average
            num_tokens = (labels != -100).sum().item()
            total_loss += outputs.loss.item() * num_tokens
            total_tokens += num_tokens

    avg_loss = total_loss / total_tokens if total_tokens > 0 else float("inf")
    perplexity = math.exp(avg_loss)
    logger.info(f"Perplexity: {perplexity:.2f} (loss={avg_loss:.4f})")
    return perplexity


def compute_token_accuracy(
    model: AutoModelForCausalLM,
    tokenizer: PreTrainedTokenizer,
    texts: list[str],
    max_length: int = 512,
    device: str = "mps",
) -> float:
    """Fraction of tokens where the model's top-1 prediction is correct.

    A supplementary signal to perplexity — easier to interpret.
    100% accuracy would mean perfect memorisation of the data.
    """
    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for text in tqdm(texts, desc="Computing token accuracy"):
            enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
            input_ids = enc["input_ids"].to(device)

            outputs = model(input_ids=input_ids)
            logits = outputs.logits  # shape: (1, seq_len, vocab_size)

            # Shift: predict token at position i using all tokens before i
            # predictions[i] should match input_ids[i+1]
            preds = logits[0, :-1, :].argmax(dim=-1)  # (seq_len - 1,)
            targets = input_ids[0, 1:]                # (seq_len - 1,)

            correct += (preds == targets).sum().item()
            total += len(targets)

    accuracy = correct / total if total > 0 else 0.0
    logger.info(f"Token accuracy: {accuracy:.4f}")
    return accuracy


def save_metrics(metrics: dict[str, Any], output_dir: str | Path) -> None:
    """Save evaluation metrics to a JSON file in the experiment directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "eval_metrics.json"
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Metrics saved to {path}")


def load_metrics(output_dir: str | Path) -> dict[str, Any]:
    """Load previously saved metrics from an experiment directory."""
    path = Path(output_dir) / "eval_metrics.json"
    with open(path) as f:
        return json.load(f)
