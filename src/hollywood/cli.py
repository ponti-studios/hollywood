from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer
from dateutil import parser as date_parser
from rich.console import Console
from rich.table import Table

from . import __version__
from .adapters import get_adapter
from .config import HollywoodSettings
from .flows import export_flow, ingest_group_flow, ingest_source_flow, normalize_flow
from .models import DoctorCheck, IngestOptions, RunStatus, RunSummary
from .registry import get_source, list_sources
from .storage import HollywoodStorage


app = typer.Typer(help="Hollywood data CLI for feeds, datasets, and directories.")
sources_app = typer.Typer(help="List built-in sources.")
ingest_app = typer.Typer(help="Run source and source-group ingests.")
app.add_typer(sources_app, name="sources")
app.add_typer(ingest_app, name="ingest")
console = Console()


def _run_ingest_source_direct(source_id: str, settings: HollywoodSettings, options: IngestOptions) -> RunSummary:
    """Run ingest without Prefect orchestration (for CLI usage)."""
    from .flows import archive_payloads_task, fetch_payloads_task, normalize_payloads_task
    from .registry import get_source as _get_source

    source = _get_source(source_id)
    storage = HollywoodStorage(settings.resolved_db_path)
    storage.initialize()
    run_id = storage.start_run(source, options.model_dump_json())
    try:
        payloads = fetch_payloads_task.fn(source, settings, options)
        archived_payloads = archive_payloads_task.fn(source, settings, payloads)
        storage.insert_raw_records(run_id, archived_payloads)
        raw_records = storage.load_raw_records(run_id=run_id)
        bundle = normalize_payloads_task.fn(source, settings, run_id, raw_records)
        storage.apply_bundle(bundle)
        summary = RunSummary(
            run_id=run_id,
            source_id=source.source_id,
            status=RunStatus.SUCCEEDED,
            raw_records=len(archived_payloads),
            normalized=bundle.counts(),
        )
        storage.finish_run(run_id, RunStatus.SUCCEEDED, summary.model_dump(mode="json"))
        return summary
    except Exception as exc:
        failure_summary = {"source_id": source.source_id, "error": str(exc)}
        storage.finish_run(run_id, RunStatus.FAILED, failure_summary, error_text=str(exc))
        raise
    finally:
        storage.close()


def _run_ingest_group_direct(group_name: str, settings: HollywoodSettings, options: IngestOptions) -> list[RunSummary]:
    """Run ingest group without Prefect."""
    summaries: list[RunSummary] = []
    for src in list_sources(group=group_name):
        summaries.append(_run_ingest_source_direct(src.source_id, settings, options))
    return summaries


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    return date_parser.parse(value)


def _build_settings(
    data_dir: Path | None,
    db_path: Path | None,
    log_level: str | None,
) -> HollywoodSettings:
    settings = HollywoodSettings()
    updates = {}
    if data_dir is not None:
        updates["data_dir"] = data_dir
    if db_path is not None:
        updates["db_path"] = db_path
    elif data_dir is not None:
        updates["db_path"] = data_dir / "hollywood.duckdb"
    if log_level is not None:
        updates["log_level"] = log_level
    if updates:
        settings = settings.model_copy(update=updates)
    settings.ensure_directories()
    return settings


def _render_checks(checks: list[DoctorCheck]) -> None:
    table = Table(title="Doctor Checks")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in checks:
        table.add_row(check.name, "ok" if check.ok else "fail", check.detail)
    console.print(table)


@sources_app.command("list")
def sources_list() -> None:
    table = Table(title=f"Hollywood Sources ({__version__})")
    table.add_column("Source")
    table.add_column("Kind")
    table.add_column("Groups")
    table.add_column("License")
    table.add_column("Full Text")
    table.add_column("Auth")
    for source in list_sources():
        table.add_row(
            source.source_id,
            source.kind.value,
            ", ".join(source.groups),
            source.license_class.value,
            "yes" if source.default_full_text else "no",
            source.api_key_env or "-",
        )
    console.print(table)


@ingest_app.command("source")
def ingest_source(
    source_id: str,
    limit: int | None = typer.Option(None, help="Maximum records to ingest for this source."),
    since: str | None = typer.Option(None, help="Only ingest records newer than this timestamp."),
    full_text: bool = typer.Option(
        True, "--full-text/--no-full-text", help="Fetch linked article text when supported."
    ),
    prefixes: str | None = typer.Option(None, help="Comma-separated or compact prefixes for WGA."),
    data_dir: Path | None = typer.Option(None, help="Override the local data directory."),
    db_path: Path | None = typer.Option(None, help="Override the DuckDB path."),
    log_level: str | None = typer.Option(None, help="Override the log level."),
) -> None:
    settings = _build_settings(data_dir, db_path, log_level)
    source = get_source(source_id)
    parsed_prefixes = None
    if prefixes:
        from .adapters.wga import normalize_prefixes

        parsed_prefixes = normalize_prefixes(prefixes)
    options = IngestOptions(
        limit=limit, since=_parse_since(since), full_text=full_text, prefixes=parsed_prefixes
    )
    summary = _run_ingest_source_direct(source.source_id, settings, options)
    console.print_json(data=summary.model_dump(mode="json"))


@ingest_app.command("group")
def ingest_group(
    group_name: str,
    limit: int | None = typer.Option(None, help="Maximum records per source."),
    since: str | None = typer.Option(None, help="Only ingest records newer than this timestamp."),
    full_text: bool = typer.Option(
        True, "--full-text/--no-full-text", help="Fetch linked article text when supported."
    ),
    data_dir: Path | None = typer.Option(None, help="Override the local data directory."),
    db_path: Path | None = typer.Option(None, help="Override the DuckDB path."),
    log_level: str | None = typer.Option(None, help="Override the log level."),
) -> None:
    settings = _build_settings(data_dir, db_path, log_level)
    options = IngestOptions(limit=limit, since=_parse_since(since), full_text=full_text)
    summaries = _run_ingest_group_direct(group_name, settings, options)
    console.print_json(data=[summary.model_dump(mode="json") for summary in summaries])


@app.command()
def normalize(
    source_id: str | None = typer.Option(None, "--source", help="Only normalize one source."),
    data_dir: Path | None = typer.Option(None, help="Override the local data directory."),
    db_path: Path | None = typer.Option(None, help="Override the DuckDB path."),
    log_level: str | None = typer.Option(None, help="Override the log level."),
) -> None:
    settings = _build_settings(data_dir, db_path, log_level)
    counts = normalize_flow(source_id, settings)
    console.print_json(data=counts)


@app.command()
def export(
    table: str | None = typer.Option(None, help="Export a single table."),
    all_tables: bool = typer.Option(False, "--all", help="Export all normalized tables."),
    file_format: str = typer.Option("parquet", "--format", help="Export format: parquet or jsonl."),
    data_dir: Path | None = typer.Option(None, help="Override the local data directory."),
    db_path: Path | None = typer.Option(None, help="Override the DuckDB path."),
    log_level: str | None = typer.Option(None, help="Override the log level."),
) -> None:
    if not all_tables and table is None:
        raise typer.BadParameter("Pass --all or --table.")
    if file_format not in {"parquet", "jsonl"}:
        raise typer.BadParameter("Export format must be 'parquet' or 'jsonl'.")
    settings = _build_settings(data_dir, db_path, log_level)
    paths = export_flow(settings, file_format, None if all_tables else table)
    console.print_json(data={"files": paths})


@app.command()
def doctor(
    data_dir: Path | None = typer.Option(None, help="Override the local data directory."),
    db_path: Path | None = typer.Option(None, help="Override the DuckDB path."),
    log_level: str | None = typer.Option(None, help="Override the log level."),
) -> None:
    settings = _build_settings(data_dir, db_path, log_level)
    storage = HollywoodStorage(settings.db_path)
    storage.initialize()
    checks = [
        DoctorCheck(name="data_dir", ok=settings.data_dir.exists(), detail=str(settings.data_dir)),
        DoctorCheck(name="db_path", ok=settings.db_path.exists(), detail=str(settings.db_path)),
        DoctorCheck(
            name="tmdb_api_key",
            ok=bool(settings.tmdb_api_key),
            detail="Configured" if settings.tmdb_api_key else "Missing",
        ),
    ]
    try:
        import playwright.sync_api  # noqa: F401

        checks.append(DoctorCheck(name="playwright", ok=True, detail="Playwright import succeeded"))
    except ImportError:
        checks.append(
            DoctorCheck(name="playwright", ok=False, detail="Playwright is not installed")
        )
    for source in list_sources():
        checks.extend(get_adapter(source).doctor_checks(settings))
    _render_checks(checks)


@app.callback()
def main() -> None:
    """Hollywood data CLI."""
