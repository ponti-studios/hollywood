from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from .models import (
    ArchivedPayload,
    NormalizedBundle,
    RunStatus,
    SourceDefinition,
    make_stable_id,
)

DDL = (
    """
    create table if not exists source_runs (
        run_id text primary key,
        source_id text,
        source_kind text,
        status text,
        started_at timestamp,
        completed_at timestamp,
        options_json text,
        summary_json text,
        error_text text
    )
    """,
    """
    create table if not exists raw_records (
        raw_record_id text primary key,
        run_id text,
        source_id text,
        source_kind text,
        payload_type text,
        logical_id text,
        source_url text,
        canonical_url text,
        content_type text,
        content_hash text,
        content_path text,
        fetched_at timestamp,
        metadata_json text
    )
    """,
    """
    create table if not exists articles (
        article_id text primary key,
        source_id text,
        canonical_url text,
        url text,
        title text,
        author text,
        published_at timestamp,
        summary text,
        feed_guid text,
        license_class text,
        run_id text,
        metadata_json text
    )
    """,
    """
    create table if not exists article_bodies (
        body_id text primary key,
        article_id text,
        source_id text,
        body_kind text,
        text text,
        raw_record_id text,
        content_hash text,
        license_class text,
        metadata_json text
    )
    """,
    """
    create table if not exists entities (
        entity_id text primary key,
        source_id text,
        external_id text,
        entity_type text,
        name text,
        canonical_name text,
        license_class text,
        metadata_json text
    )
    """,
    """
    create table if not exists entity_aliases (
        entity_alias_id text primary key,
        entity_id text,
        source_id text,
        alias text,
        metadata_json text
    )
    """,
    """
    create table if not exists article_entities (
        article_entity_id text primary key,
        article_id text,
        entity_id text,
        source_id text,
        relation text,
        metadata_json text
    )
    """,
    """
    create table if not exists credits (
        credit_id text primary key,
        source_id text,
        person_entity_id text,
        person_name text,
        title_name text,
        title_external_id text,
        role text,
        billing integer,
        metadata_json text
    )
    """,
)


class HollywoodStorage:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()

    def connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            for statement in DDL:
                conn.execute(statement)

    def start_run(self, source: SourceDefinition, options_json: str) -> str:
        run_id = make_stable_id(source.source_id, options_json, datetime.now(UTC).isoformat())
        with self.connect() as conn:
            conn.execute(
                """
                insert into source_runs (
                    run_id, source_id, source_kind, status, started_at, completed_at, options_json, summary_json, error_text
                ) values (?, ?, ?, ?, now(), null, ?, '{}', null)
                """,
                [
                    run_id,
                    source.source_id,
                    source.kind.value,
                    RunStatus.RUNNING.value,
                    options_json,
                ],
            )
        return run_id

    def finish_run(
        self, run_id: str, status: RunStatus, summary: dict[str, Any], error_text: str | None = None
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                update source_runs
                set status = ?, completed_at = now(), summary_json = ?, error_text = ?
                where run_id = ?
                """,
                [
                    status.value,
                    json.dumps(summary, ensure_ascii=False, sort_keys=True),
                    error_text,
                    run_id,
                ],
            )

    def insert_raw_records(self, run_id: str, archived_payloads: Iterable[ArchivedPayload]) -> None:
        rows = []
        for payload in archived_payloads:
            rows.append(
                {
                    "raw_record_id": payload.raw_record_id,
                    "run_id": run_id,
                    "source_id": payload.source_id,
                    "source_kind": payload.source_kind,
                    "payload_type": payload.payload_type,
                    "logical_id": payload.logical_id,
                    "source_url": payload.source_url,
                    "canonical_url": payload.canonical_url,
                    "content_type": payload.content_type,
                    "content_hash": payload.content_hash,
                    "content_path": payload.content_path,
                    "fetched_at": payload.fetched_at,
                    "metadata_json": payload.metadata_json,
                }
            )
        self._upsert_dicts("raw_records", rows, ("raw_record_id",))

    def apply_bundle(self, bundle: NormalizedBundle) -> None:
        self._upsert_models("articles", bundle.articles, ("article_id",))
        self._upsert_models("article_bodies", bundle.article_bodies, ("body_id",))
        self._upsert_models("entities", bundle.entities, ("entity_id",))
        self._upsert_models("entity_aliases", bundle.entity_aliases, ("entity_alias_id",))
        self._upsert_models("article_entities", bundle.article_entities, ("article_entity_id",))
        self._upsert_models("credits", bundle.credits, ("credit_id",))

    def load_raw_records(
        self, source_id: str | None = None, run_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = "select * from raw_records"
        conditions: list[str] = []
        params: list[Any] = []
        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        if run_id:
            conditions.append("run_id = ?")
            params.append(run_id)
        if conditions:
            query += " where " + " AND ".join(conditions)
        query += " order by fetched_at asc"
        with self.connect() as conn:
            arrow_table = conn.execute(query, params).to_arrow_table()
        return pl.DataFrame(arrow_table).to_dicts()

    def table_count(self, table: str) -> int:
        with self.connect() as conn:
            row = conn.execute(f"select count(*) from {table}").fetchone()
        return int(row[0]) if row is not None else 0

    def export_table(self, table: str, output_dir: Path, file_format: str) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{table}.{'parquet' if file_format == 'parquet' else 'jsonl'}"
        with self.connect() as conn:
            if file_format == "parquet":
                conn.execute(f"COPY (SELECT * FROM {table}) TO ? (FORMAT PARQUET)", [str(path)])
            else:
                frame = pl.DataFrame(conn.execute(f"select * from {table}").to_arrow_table())
                frame.write_ndjson(path)
        return path

    def export_all(self, output_dir: Path, file_format: str) -> list[Path]:
        return [
            self.export_table(table, output_dir, file_format)
            for table in (
                "source_runs",
                "raw_records",
                "articles",
                "article_bodies",
                "entities",
                "entity_aliases",
                "article_entities",
                "credits",
            )
        ]

    def _upsert_models(self, table: str, rows: Iterable[Any], key_cols: tuple[str, ...]) -> None:
        payload = [row.model_dump(mode="python") for row in rows]
        self._upsert_dicts(table, payload, key_cols)

    def _upsert_dicts(
        self, table: str, rows: list[dict[str, Any]], key_cols: tuple[str, ...]
    ) -> None:
        if not rows:
            return
        # Deduplicate on key columns in case the bundle has the same entity
        # appearing multiple times (e.g., same person credited in multiple titles)
        seen: set[tuple] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            key = tuple(row.get(col) for col in key_cols)
            if key not in seen:
                seen.add(key)
                deduped.append(row)
        frame = pl.DataFrame(deduped, strict=False)
        key_match = " AND ".join(f"t.{column} = s.{column}" for column in key_cols)
        column_list = ", ".join(frame.columns)
        with self.connect() as conn:
            conn.register("_incoming", frame.to_arrow())
            conn.execute(f"DELETE FROM {table} AS t USING _incoming AS s WHERE {key_match}")
            conn.execute(f"INSERT INTO {table} ({column_list}) SELECT {column_list} FROM _incoming")
            conn.unregister("_incoming")
