"""
train.py — CLI commands for running posttraining recipes.

Usage:
  nexus train run --recipe configs/recipes/sft_lora.yaml
  nexus train run --recipe configs/recipes/dpo.yaml --no-wandb
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from nexus.config import Recipe
from nexus.runtime import ensure_apple_runtime

train_app = typer.Typer(no_args_is_help=True)
console = Console()


@train_app.command("run")
def run(
    recipe: Path = typer.Option(
        ...,
        "--recipe",
        "-r",
        help="Path to the YAML recipe file (e.g. configs/recipes/sft_lora.yaml)",
        exists=True,
    ),
    no_wandb: bool = typer.Option(
        False,
        "--no-wandb",
        help="Disable W&B logging for this run.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Load and validate the config without starting training.",
    ),
) -> None:
    """Run a posttraining recipe from a YAML config file.

    The recipe file specifies which model to use, which dataset to train on,
    which training method to apply (SFT / DPO / ORPO / GRPO), and all
    hyperparameters. See configs/recipes/ for examples.
    """
    # ── Load and validate config ──────────────────────────────────────────
    console.print(f"\n[bold]Loading recipe:[/bold] {recipe}")
    try:
        cfg = Recipe.from_yaml(recipe)
    except Exception as e:
        console.print(f"[red]Invalid recipe:[/red] {e}")
        raise typer.Exit(code=1)

    if no_wandb:
        cfg.wandb.enabled = False

    # Print a summary panel
    console.print(
        Panel(
            f"[bold]{cfg.name}[/bold]\n"
            f"[dim]{cfg.description}[/dim]\n\n"
            f"  Model:   {cfg.model.model_id}\n"
            f"  Method:  [cyan]{cfg.training.method.upper()}[/cyan]\n"
            f"  Dataset: {cfg.data.dataset_name}\n"
            f"  LoRA:    {'rank=' + str(cfg.lora.rank) if cfg.lora else 'disabled'}\n"
            f"  Output:  {cfg.resolve_output_dir()}\n"
            f"  W&B:     {'enabled' if cfg.wandb.enabled else 'disabled'}",
            title="Training Recipe",
            border_style="blue",
        )
    )

    if dry_run:
        console.print("[yellow]Dry run — skipping training.[/yellow]")
        return

    ensure_apple_runtime(console)

    from nexus.device import print_device_info

    # ── Dispatch to the right trainer ─────────────────────────────────────
    print_device_info()

    method = cfg.training.method

    if method == "sft":
        from nexus.trainers.sft import run_sft

        run_sft(cfg)
    elif method == "dpo":
        from nexus.trainers.dpo import run_dpo

        run_dpo(cfg)
    elif method == "orpo":
        from nexus.trainers.orpo import run_orpo

        run_orpo(cfg)
    elif method == "grpo":
        from nexus.trainers.grpo import run_grpo

        run_grpo(cfg)
    else:
        console.print(f"[red]Unknown training method: {method}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[green]✓ Training complete.[/green] Results in: {cfg.resolve_output_dir()}")
