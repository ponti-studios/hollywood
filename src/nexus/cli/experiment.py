"""
experiment.py — CLI commands for running benchmark experiments.

Commands:
  nexus experiment run   --config experiments/configs/exp_01.yaml
  nexus experiment run   --phase 1 --samples 50 --no-wandb
  nexus experiment list  (show available experiment configs)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

experiment_app = typer.Typer(no_args_is_help=True)
console = Console()


@experiment_app.command("run")
def run_experiment(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to experiment YAML config file.",
    ),
    phase: int = typer.Option(
        1,
        "--phase", "-p",
        help="Which experiment phase to run (1–4). Ignored if --config is provided.",
        min=1,
        max=4,
    ),
    small_model: str = typer.Option(
        "google/gemma-3-4b-it",
        "--small-model",
        help="Small model to evaluate.",
    ),
    large_model: Optional[str] = typer.Option(
        None,
        "--large-model",
        help="Large reference model for comparison (optional).",
    ),
    samples: int = typer.Option(
        500,
        "--samples", "-n",
        help="Number of questions per benchmark. Use 50 for a quick sanity check.",
    ),
    no_wandb: bool = typer.Option(
        False,
        "--no-wandb",
        help="Disable Weights & Biases logging.",
    ),
) -> None:
    """Run a benchmark experiment.

    Examples:

    \b
    # Run Phase 1 baseline with defaults (500 samples, gemma-3-4b-it):
    nexus experiment run

    \b
    # Quick sanity check (50 samples, no W&B):
    nexus experiment run --samples 50 --no-wandb

    \b
    # Run from a YAML config file:
    nexus experiment run --config experiments/configs/exp_01.yaml

    \b
    # Compare small vs large model:
    nexus experiment run --large-model meta-llama/Meta-Llama-3-70B-Instruct
    """
    if phase == 1:
        _run_phase_1(config, small_model, large_model, samples, no_wandb)
    else:
        console.print(
            f"[yellow]Phase {phase} is not yet implemented.[/yellow] "
            f"Only Phase 1 (baseline) is available right now."
        )
        raise typer.Exit(code=1)


def _run_phase_1(
    config: Optional[Path],
    small_model: str,
    large_model: Optional[str],
    samples: int,
    no_wandb: bool,
) -> None:
    """Dispatch to the Phase 1 baseline runner."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

    from nexus.experiments.config import (
        ExperimentConfig, ModelSpec, BenchmarkSpec, LoggingSpec, SyntheticPuzzleSpec
    )

    if config is not None:
        if not config.exists():
            console.print(f"[red]Config file not found:[/red] {config}")
            raise typer.Exit(code=1)
        cfg = ExperimentConfig.from_yaml(config)
    else:
        models = [ModelSpec(model_id=small_model, role="small")]
        if large_model:
            models.append(ModelSpec(model_id=large_model, role="large"))

        cfg = ExperimentConfig(
            name="exp_01_baseline",
            description="Phase 1: Closed-book baseline",
            phase=1,
            models=models,
            benchmarks=[
                BenchmarkSpec(name="triviaqa", samples=samples),
                BenchmarkSpec(name="mmlu", samples=samples),
                BenchmarkSpec(name="synthetic", samples=samples),
            ],
            synthetic=SyntheticPuzzleSpec(),
            logging=LoggingSpec(wandb_project=None if no_wandb else "3b-logic-broker"),
        )

    # Import here so the CLI startup stays fast (avoids loading torch on --help)
    from experiments.exp_01_baseline import BaselineRunner
    runner = BaselineRunner(cfg)
    runner.execute()


@experiment_app.command("list")
def list_experiments(
    configs_dir: Path = typer.Option(
        Path("experiments/configs"),
        "--dir",
        help="Directory to scan for experiment YAML configs.",
    ),
) -> None:
    """List all available experiment config files."""
    if not configs_dir.exists():
        console.print(f"[yellow]No configs directory found at {configs_dir}[/yellow]")
        raise typer.Exit(code=0)

    yaml_files = sorted(configs_dir.glob("*.yaml"))
    if not yaml_files:
        console.print(f"[yellow]No YAML configs found in {configs_dir}[/yellow]")
        raise typer.Exit(code=0)

    table = Table(title="Available Experiment Configs", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Name")
    table.add_column("Phase", justify="center")
    table.add_column("Description")

    from nexus.experiments.config import ExperimentConfig
    for path in yaml_files:
        try:
            cfg = ExperimentConfig.from_yaml(path)
            table.add_row(path.name, cfg.name, str(cfg.phase), cfg.description[:60] + "…")
        except Exception as e:
            table.add_row(path.name, "[red]parse error[/red]", "—", str(e)[:60])

    console.print(table)
