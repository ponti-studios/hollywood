"""
loaders.py — Load and split HuggingFace datasets for training.

Concepts
────────
A "dataset" in ML is a collection of (input, expected_output) pairs.
For language model fine-tuning the inputs are text prompts and the
outputs are the desired model responses.

HuggingFace hosts thousands of open datasets at huggingface.co/datasets.
The `datasets` library downloads and caches them locally on first use.

Train / Validation split
────────────────────────
We never train and evaluate on the same data. The model would simply
memorise the training examples, which is called "overfitting".

  train set  — examples the model learns from (95% by default)
  val set    — examples held out to measure real generalisation (5%)

The validation loss is the most important number to watch during training:
  - If train loss ↓ but val loss ↑  → overfitting (too much training)
  - If both losses ↓                → healthy learning
  - If both losses plateau          → try a higher learning rate
"""

from __future__ import annotations

import logging

from datasets import Dataset, DatasetDict, load_dataset
from rich.console import Console

from nexus.config import DataConfig

logger = logging.getLogger(__name__)
console = Console()


def load_and_split(cfg: DataConfig) -> DatasetDict:
    """Download (or load from cache) a dataset and create train/val splits.

    Args:
        cfg: DataConfig specifying which dataset and how to process it.

    Returns:
        A DatasetDict with "train" and "validation" keys.
    """
    console.print(f"[bold]Loading dataset:[/bold] {cfg.dataset_name} (split={cfg.split})")

    dataset = load_dataset(
        cfg.dataset_name,
        split=cfg.split,
        trust_remote_code=True,  # required by some datasets
    )

    # Optionally cap the number of examples for quick experiments
    if cfg.max_samples is not None:
        dataset = dataset.select(range(min(cfg.max_samples, len(dataset))))  # type: ignore
        console.print(f"  Capped at {cfg.max_samples} samples")

    console.print(f"  Total examples: {len(dataset)}")  # type: ignore

    # Create train / validation split
    # shuffle=True is important so the val set isn't all from one part of the dataset
    split = dataset.train_test_split(  # type: ignore
        test_size=cfg.val_split,
        seed=cfg.seed,
        shuffle=True,
    )

    result = DatasetDict({"train": split["train"], "validation": split["test"]})

    console.print(f"  Train: {len(result['train'])} | Val: {len(result['validation'])}")
    return result


def inspect_dataset(dataset: Dataset, num_examples: int = 3) -> None:
    """Print a few examples from the dataset so you can see what it looks like."""
    console.print(f"\n[bold]Dataset sample ({num_examples} examples)[/bold]")
    console.print(f"  Columns: {dataset.column_names}")
    console.print(f"  Total rows: {len(dataset)}\n")

    for i in range(min(num_examples, len(dataset))):
        console.print(f"[dim]── Example {i + 1} ──────────────────────────[/dim]")
        for key, value in dataset[i].items():
            # Truncate long strings for display
            display = str(value)
            if len(display) > 200:
                display = display[:200] + " …"
            console.print(f"  [cyan]{key}[/cyan]: {display}")
        console.print()
