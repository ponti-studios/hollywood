"""
data.py — CLI commands for downloading and inspecting datasets.

Usage:
  nexus data download --name tatsu-lab/alpaca
  nexus data inspect  --name tatsu-lab/alpaca
  nexus data list
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

data_app = typer.Typer(no_args_is_help=True)
console = Console()

# Curated list of datasets useful for Gemma posttraining experiments
RECOMMENDED_DATASETS = {
    # SFT datasets
    "tatsu-lab/alpaca": {
        "method": "sft",
        "size": "52K",
        "description": "Classic instruction-following dataset. Good for learning SFT basics.",
    },
    "HuggingFaceH4/ultrachat_200k": {
        "method": "sft",
        "size": "200K",
        "description": "High-quality multi-turn conversations. Better quality than Alpaca.",
    },
    "teknium/OpenHermes-2.5": {
        "method": "sft",
        "size": "1M",
        "description": "Large, diverse instruction dataset. Great for stronger SFT.",
    },
    # Preference datasets (DPO / ORPO)
    "trl-lib/ultrafeedback_binarized": {
        "method": "dpo/orpo",
        "size": "61K",
        "description": "Preference pairs from UltraFeedback. Standard DPO benchmark.",
    },
    "Anthropic/hh-rlhf": {
        "method": "dpo",
        "size": "161K",
        "description": "Human feedback on helpfulness and harmlessness from Anthropic.",
    },
    # Reasoning (GRPO)
    "gsm8k": {
        "method": "grpo",
        "size": "8.5K",
        "description": "Grade school math word problems. Classic GRPO reasoning benchmark.",
    },
    "lighteval/MATH": {
        "method": "grpo",
        "size": "12.5K",
        "description": "Competition math problems. More challenging than GSM8K.",
    },
}


@data_app.command("list")
def list_datasets() -> None:
    """Show recommended datasets for each training method."""
    table = Table(title="Recommended Datasets", show_header=True, header_style="bold cyan")
    table.add_column("Dataset", style="white")
    table.add_column("Method", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Description")

    for name, info in RECOMMENDED_DATASETS.items():
        table.add_row(name, info["method"], info["size"], info["description"])

    console.print(table)
    console.print("\nDownload any of these with: [cyan]nexus data download --name <dataset>[/cyan]")


@data_app.command("download")
def download(
    name: str = typer.Option(..., "--name", "-n", help="HuggingFace dataset name."),
    split: str = typer.Option("train", "--split", help="Which split to download."),
    max_samples: int = typer.Option(
        0,
        "--max-samples",
        help="Cap number of samples (0 = download all).",
    ),
) -> None:
    """Download and cache a HuggingFace dataset locally.

    Downloaded datasets are cached in ~/.cache/huggingface/datasets/
    and won't be re-downloaded on subsequent runs.
    """
    from datasets import load_dataset
    from nexus.data.loaders import inspect_dataset

    console.print(f"\n[bold]Downloading:[/bold] {name} (split={split})")

    kwargs: dict = {"split": split, "trust_remote_code": True}
    ds = load_dataset(name, **kwargs)

    if max_samples and max_samples > 0:
        ds = ds.select(range(min(max_samples, len(ds))))  # type: ignore

    console.print(f"[green]✓ Downloaded {len(ds)} examples.[/green]")  # type: ignore
    inspect_dataset(ds, num_examples=2)  # type: ignore


@data_app.command("inspect")
def inspect(
    name: str = typer.Option(..., "--name", "-n", help="HuggingFace dataset name."),
    split: str = typer.Option("train", "--split"),
    num_examples: int = typer.Option(5, "--num-examples", help="How many examples to show."),
) -> None:
    """Preview a dataset without fully downloading it (uses streaming)."""
    from datasets import load_dataset
    from nexus.data.loaders import inspect_dataset

    console.print(f"\n[bold]Inspecting:[/bold] {name}")

    ds = load_dataset(name, split=split, streaming=True, trust_remote_code=True)
    # Take the first N examples from the stream
    examples = list(ds.take(num_examples))  # type: ignore

    from datasets import Dataset
    preview = Dataset.from_list(examples)
    inspect_dataset(preview, num_examples=num_examples)
