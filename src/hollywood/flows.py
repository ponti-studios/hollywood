from __future__ import annotations

from collections import defaultdict

from prefect import flow, task

from .adapters import get_adapter
from .archive import archive_payload
from .config import HollywoodSettings
from .models import IngestOptions, RunStatus, RunSummary, SourceDefinition
from .registry import get_source, list_sources
from .storage import HollywoodStorage


@task
def fetch_payloads_task(
    source: SourceDefinition, settings: HollywoodSettings, options: IngestOptions
):
    adapter = get_adapter(source)
    return adapter.fetch_raw_payloads(settings, options)


@task
def archive_payloads_task(source: SourceDefinition, settings: HollywoodSettings, payloads):
    return [archive_payload(settings, source, payload) for payload in payloads]


@task
def normalize_payloads_task(
    source: SourceDefinition,
    settings: HollywoodSettings,
    storage: HollywoodStorage,
    run_id: str,
    raw_records: list[dict[str, object]],
):
    adapter = get_adapter(source)
    return adapter.normalize_raw_records(settings, storage, run_id, raw_records)


@flow(name="hollywood-ingest-source")
def ingest_source_flow(
    source_id: str, settings: HollywoodSettings, options: IngestOptions
) -> RunSummary:
    source = get_source(source_id)
    storage = HollywoodStorage(settings.resolved_db_path)
    storage.initialize()
    run_id = storage.start_run(source, options.model_dump_json())
    try:
        payloads = fetch_payloads_task(source, settings, options)
        archived_payloads = archive_payloads_task(source, settings, payloads)
        storage.insert_raw_records(run_id, archived_payloads)
        raw_records = storage.load_raw_records(run_id=run_id)
        bundle = normalize_payloads_task(source, settings, storage, run_id, raw_records)
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


@flow(name="hollywood-ingest-group")
def ingest_group_flow(
    group_name: str, settings: HollywoodSettings, options: IngestOptions
) -> list[RunSummary]:
    summaries: list[RunSummary] = []
    for source in list_sources(group=group_name):
        summaries.append(ingest_source_flow(source.source_id, settings, options))
    return summaries


@flow(name="hollywood-normalize")
def normalize_flow(source_id: str | None, settings: HollywoodSettings) -> dict[str, int]:
    storage = HollywoodStorage(settings.resolved_db_path)
    storage.initialize()
    grouped_records: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in storage.load_raw_records(source_id=source_id):
        grouped_records[str(record["source_id"])].append(record)

    combined_counts = defaultdict(int)
    for grouped_source_id, records in grouped_records.items():
        source = get_source(grouped_source_id)
        adapter = get_adapter(source)
        run_id = f"normalize::{grouped_source_id}"
        bundle = adapter.normalize_raw_records(settings, storage, run_id, records)
        storage.apply_bundle(bundle)
        for key, value in bundle.counts().items():
            combined_counts[key] += value
    return dict(combined_counts)


def export_flow(
    settings: HollywoodSettings, file_format: str, table: str | None = None
) -> list[str]:
    storage = HollywoodStorage(settings.resolved_db_path)
    storage.initialize()
    if table:
        return [str(storage.export_table(table, settings.parquet_dir, file_format))]
    return [str(path) for path in storage.export_all(settings.parquet_dir, file_format)]
