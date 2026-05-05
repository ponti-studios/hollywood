"""
experiment.py — CLI commands for running benchmark experiments.

Commands:
  nexus experiment run --phase 1
  nexus experiment list  (show available experiment configs)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

experiment_app = typer.Typer(no_args_is_help=True)
cache_app = typer.Typer(no_args_is_help=True)
console = Console()

PRESET_CONFIGS: dict[int, Path] = {
    1: Path("configs/benchmarks/exp_01.yaml"),
    2: Path("configs/benchmarks/exp_02.yaml"),
    3: Path("configs/benchmarks/exp_03.yaml"),
}

experiment_app.add_typer(cache_app, name="cache")


@experiment_app.command("run")
def run_experiment(
    phase: int = typer.Option(
        1,
        "--phase",
        "-p",
        help="Which standard experiment phase to run.",
        min=1,
        max=3,
    ),
) -> None:
    """Run one of the fixed benchmark experiment presets.

    The preset YAML files in configs/benchmarks/ are the canonical source of
    truth. This command intentionally does not accept ad hoc model, sample,
    cache, or W&B overrides.
    """
    if phase not in PRESET_CONFIGS:
        console.print(
            f"[yellow]Phase {phase} is not yet implemented.[/yellow] "
            f"Available phases: {', '.join(str(p) for p in sorted(PRESET_CONFIGS))}."
        )
        raise typer.Exit(code=1)

    config = PRESET_CONFIGS[phase]
    from nexus.experiments.config import ExperimentConfig

    if not config.exists():
        console.print(f"[red]Preset config file not found:[/red] {config}")
        raise typer.Exit(code=1)

    cfg = ExperimentConfig.from_yaml(config)

    if phase == 1:
        from nexus.experiments.phases.baseline import BaselineRunner

        runner = BaselineRunner(cfg)
    elif phase == 2:
        from nexus.experiments.phases.open_book import OpenBookRunner

        runner = OpenBookRunner(cfg)
    else:
        from nexus.experiments.phases.reflection import ReflectionRunner

        runner = ReflectionRunner(cfg)

    runner.execute()


@experiment_app.command("list")
def list_experiments(
    configs_dir: Path = typer.Option(
        Path("configs/benchmarks"),
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


@cache_app.command("list")
def list_reference_caches(
    cache_dir: Path = typer.Option(
        Path(".data/benchmarks/cache"),
        "--dir",
        help="Directory containing reference cache entries.",
    ),
    experiment: str | None = typer.Option(None, "--experiment", help="Filter by experiment name."),
    model: str | None = typer.Option(None, "--model", help="Filter by exact model id."),
    benchmark: str | None = typer.Option(None, "--benchmark", help="Filter by benchmark name."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON output."),
) -> None:
    """List reference cache entries."""
    from nexus.experiments.reference_cache import find_reference_caches, summarize_cache_file

    matches = find_reference_caches(
        cache_dir, experiment=experiment, model=model, benchmark=benchmark
    )
    if not matches:
        if as_json:
            console.print_json(data=[])
        else:
            console.print("[yellow]No reference caches matched the requested filters.[/yellow]")
        raise typer.Exit(code=0)

    summaries = [summarize_cache_file(cache_path) for cache_path in matches]

    if as_json:
        console.print_json(
            data=[
                {
                    **summary,
                    "path": str(summary["path"]),
                }
                for summary in summaries
            ]
        )
        raise typer.Exit(code=0)

    table = Table(title="Reference Caches", show_lines=True)
    table.add_column("Experiment", style="magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Benchmark")
    table.add_column("Accuracy", justify="right")
    table.add_column("Created", justify="right")
    table.add_column("Path")

    for cache_path, summary in zip(matches, summaries, strict=False):
        created_at = summary.get("created_at")
        created = (
            datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
            if isinstance(created_at, int)
            else "—"
        )
        table.add_row(
            str(summary.get("experiment") or "—"),
            str(summary.get("model_id") or "—").split("/")[-1],
            str(summary.get("benchmark") or "—"),
            f"{summary['accuracy'] * 100:.1f}% ({summary['correct']}/{summary['total']})",
            created,
            str(cache_path),
        )

    console.print(table)


@cache_app.command("inspect")
def inspect_reference_cache(
    cache_path: Path = typer.Argument(..., exists=True, help="Path to a cache JSON file."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON output."),
) -> None:
    """Inspect one reference cache entry in detail."""
    from nexus.experiments.reference_cache import read_cache_metadata, summarize_cache_file

    summary = summarize_cache_file(cache_path)
    payload = read_cache_metadata(cache_path)

    if as_json:
        console.print_json(
            data={
                "summary": {**summary, "path": str(summary["path"])},
                "results_preview": payload.get("results", [])[:5],
                "results_total": len(payload.get("results", [])),
            }
        )
        raise typer.Exit(code=0)

    console.print(f"Path: [cyan]{cache_path}[/cyan]")
    console.print(f"Experiment: {summary['experiment']}")
    console.print(f"Model: {summary['model_id']}")
    console.print(f"Role: {summary['role']}")
    console.print(f"Benchmark: {summary['benchmark']}")
    console.print(
        f"Accuracy: {summary['accuracy'] * 100:.1f}% ({summary['correct']}/{summary['total']})"
    )
    console.print(f"Signature: {summary['benchmark_signature']}")
    console.print(f"Score Version: {summary['score_version']}")
    created_at = summary.get("created_at")
    if isinstance(created_at, int):
        console.print(
            f"Created: {datetime.fromtimestamp(created_at).isoformat(timespec='seconds')}"
        )

    results = payload.get("results", [])
    preview = Table(title="Cached Result Preview", show_lines=True)
    preview.add_column("Question ID", style="magenta")
    preview.add_column("Correct", justify="center")
    preview.add_column("Prediction")

    for item in results[:5]:
        preview.add_row(
            item.get("id", "—"),
            "yes" if item.get("correct") else "no",
            str(item.get("predicted", ""))[:100],
        )

    console.print(preview)
    if len(results) > 5:
        console.print(f"[dim]{len(results) - 5} more cached results omitted.[/dim]")


@cache_app.command("purge")
def purge_reference_cache(
    cache_path: Path | None = typer.Argument(None, help="Specific cache JSON file to delete."),
    cache_dir: Path = typer.Option(
        Path(".data/benchmarks/cache"),
        "--dir",
        help="Directory containing reference cache entries.",
    ),
    experiment: str | None = typer.Option(None, "--experiment", help="Filter by experiment name."),
    model: str | None = typer.Option(None, "--model", help="Filter by exact model id."),
    benchmark: str | None = typer.Option(None, "--benchmark", help="Filter by benchmark name."),
    yes: bool = typer.Option(False, "--yes", help="Confirm deletion without prompting."),
) -> None:
    """Delete one or more reference cache entries."""
    from nexus.experiments.reference_cache import find_reference_caches

    if cache_path is not None:
        targets = [cache_path]
    else:
        targets = find_reference_caches(
            cache_dir, experiment=experiment, model=model, benchmark=benchmark
        )

    if not targets:
        console.print("[yellow]No reference caches matched the requested filters.[/yellow]")
        raise typer.Exit(code=0)

    if not yes:
        console.print(
            f"[yellow]Refusing to delete {len(targets)} cache file(s) without --yes.[/yellow]"
        )
        raise typer.Exit(code=1)

    deleted = 0
    for target in targets:
        if target.exists() and target.is_file():
            target.unlink()
            deleted += 1

    console.print(f"Deleted [cyan]{deleted}[/cyan] reference cache file(s).")
