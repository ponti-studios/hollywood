"""SQLite storage layer for the unified Hollywood database.

Replaces the DuckDB storage layer. Uses sqlite3 with WAL mode,
Goose-managed migrations, and dict-based row handling.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    ArchivedPayload,
    NormalizedBundle,
    RunStatus,
    SourceDefinition,
    make_stable_id,
)

# Map model field names → unified schema column names.
# Model fields use descriptive names (article_id, entity_id) but the
# unified schema uses `id` as the primary key in every table.
_COLUMN_MAP: dict[str, dict[str, str]] = {
    "runs": {
        "run_id": "id",
        "source_id": "source_id",
        "source_kind": "source_kind",  # mapped from RunStatus + logic
        "status": "status",
        "started_at": "started_at",
        "completed_at": "completed_at",
        "options_json": "options_json",
        "summary_json": "summary_json",
        "error_text": "error_text",
    },
    # "raw_records" is built directly with DB columns in insert_raw_records —
    # no mapping needed. Other tables use model field → DB column mapping.
    "articles": {
        "article_id": "id",
        "source_id": "source_id",
        "canonical_url": "canonical_url",
        "url": "url",
        "title": "title",
        "author": "author",
        "published_at": "published_at",
        "summary": "summary",
        "feed_guid": "feed_guid",
        "license_class": "license_class",
        "run_id": "run_id",
        "metadata_json": "metadata_json",
    },
    "article_content": {
        "content_id": "id",
        "article_id": "article_id",
        "source_id": "source_id",
        "content_kind": "content_kind",
        "text": "text",
        "raw_record_id": "raw_record_id",
        "content_hash": "content_hash",
        "license_class": "license_class",
        "metadata_json": "metadata_json",
    },
    "entities": {
        "entity_id": "id",
        "source_id": "source_id",
        "external_id": "external_id",
        "entity_type": "entity_type",
        "name": "name",
        "canonical_name": "canonical_name",
        "license_class": "license_class",
        "metadata_json": "metadata_json",
    },
    "entity_aliases": {
        "entity_alias_id": "id",
        "entity_id": "entity_id",
        "source_id": "source_id",
        "alias": "alias",
    },
    "article_entities": {
        "article_entity_id": "id",
        "article_id": "article_id",
        "entity_id": "entity_id",
        "source_id": "source_id",
        "relation": "relation",
        "metadata_json": "metadata_json",
    },
    "credits": {
        "credit_id": "id",
        "source_id": "source_id",
        "person_entity_id": "person_id",
        "title_entity_id": "title_id",
        "person_name": None,  # discarded — use entity lookup
        "title_name": None,  # discarded — use entity lookup
        "title_external_id": None,  # discarded — use entity lookup
        "role": "role",
        "billing": "billing",
        "metadata_json": "metadata_json",
    },
}

# Columns that require defaults not present in the model
_DEFAULTS: dict[str, dict[str, Any]] = {
    "runs": {"run_kind": "ingest"},
    "entities": {
        "status": "active",
        "created_at": None,  # filled at insert time
        "updated_at": None,  # filled at insert time
    },
    "entity_aliases": {"created_at": None},
    "credits": {
        "credit_type": "cast",
        "trust_state": "machine_extracted",
        "created_at": None,
    },
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class HollywoodStorage:
    """SQLite-backed storage for the Hollywood pipeline.

    Uses the unified schema at ~/.hominem/hollywood.db (or any path).
    Migrations are managed by Goose — this class only reads/writes.

    Maintains a single connection for the lifetime of the object to avoid
    SQLite locking issues with Prefect's multiprocess flow execution.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA foreign_keys=ON")
            self._conn = conn
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        self.close()

    def initialize(self) -> None:
        """Ensure the database file exists. Migrations run separately via Goose."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            # Touch the DB to create it — don't reuse self._conn
            tmp = sqlite3.connect(str(self.db_path))
            tmp.execute("PRAGMA journal_mode=DELETE")
            tmp.close()

    # ── run tracking ──────────────────────────────────────────────

    def start_run(self, source: SourceDefinition, options_json: str) -> str:
        run_id = make_stable_id(source.source_id, options_json, _now())
        conn = self.connect()
        conn.execute(
            """INSERT INTO runs (id, source_id, run_kind, status, started_at, options_json)
               VALUES (?, ?, 'ingest', ?, ?, ?)""",
            (run_id, source.source_id, RunStatus.RUNNING.value, _now(), options_json),
        )
        conn.commit()
        return run_id

    def finish_run(
        self,
        run_id: str,
        status: RunStatus,
        summary: dict[str, Any],
        error_text: str | None = None,
    ) -> None:
        conn = self.connect()
        conn.execute(
            """UPDATE runs SET status = ?, completed_at = ?, summary_json = ?, error_text = ?
               WHERE id = ?""",
            (
                status.value,
                _now(),
                json.dumps(summary, ensure_ascii=False, sort_keys=True),
                error_text,
                run_id,
            ),
        )
        conn.commit()

    # ── raw records ───────────────────────────────────────────────

    def insert_raw_records(self, run_id: str, archived_payloads: Iterable[ArchivedPayload]) -> None:
        rows: list[dict[str, Any]] = []
        for p in archived_payloads:
            rows.append({
                "id": p.raw_record_id,
                "run_id": run_id,
                "source_id": p.source_id,
                "source_kind": p.source_kind,
                "payload_type": p.payload_type,
                "content_path": p.content_path,
                "content_hash": p.content_hash,
                "content_type": p.content_type,
                "source_url": p.source_url,
                "canonical_url": p.canonical_url,
                "fetched_at": p.fetched_at.isoformat()
                if hasattr(p.fetched_at, "isoformat")
                else str(p.fetched_at),
                "metadata_json": p.metadata_json,
            })
        self._upsert_dicts("raw_records", rows, ("id",))

    def load_raw_records(
        self, source_id: str | None = None, run_id: str | None = None
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        if run_id:
            conditions.append("run_id = ?")
            params.append(run_id)
        query = "SELECT * FROM raw_records"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY fetched_at ASC"

        conn = self.connect()
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ── normalized bundle ─────────────────────────────────────────

    def apply_bundle(self, bundle: NormalizedBundle) -> None:
        self._upsert_models("articles", bundle.articles, ("id",))
        self._upsert_models("article_content", bundle.article_content, ("id",))
        self._upsert_models("entities", bundle.entities, ("id",))
        self._upsert_models("entity_aliases", bundle.entity_aliases, ("id",))
        self._upsert_models("article_entities", bundle.article_entities, ("id",))
        self._upsert_models("credits", bundle.credits, ("id",))

    # ── counts / exports ──────────────────────────────────────────

    def table_count(self, table: str) -> int:
        conn = self.connect()
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0

    def export_table(self, table: str, output_dir: Path, file_format: str) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = "parquet" if file_format == "parquet" else "jsonl"
        path = output_dir / f"{table}.{ext}"

        conn = self.connect()
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        records = [dict(r) for r in rows]

        if file_format == "parquet":
            import pyarrow as pa
            import pyarrow.parquet as pq

            if records:
                table_arrow = pa.Table.from_pylist(records)
                pq.write_table(table_arrow, path)
            else:
                pq.write_table(pa.table({}), path)
        else:
            with open(path, "w") as f:
                for record in records:
                    f.write(json.dumps(record, default=str) + "\n")

        return path

    def export_all(self, output_dir: Path, file_format: str) -> list[Path]:
        tables = (
            "runs",
            "raw_records",
            "articles",
            "article_content",
            "article_entities",
            "entities",
            "entity_aliases",
            "credits",
        )
        return [self.export_table(table, output_dir, file_format) for table in tables]

    # ── internal upsert ──────────────────────────────────────────

    def _upsert_models(self, table: str, rows: Iterable[Any], key_cols: tuple[str, ...]) -> None:
        payload: list[dict[str, Any]] = []
        for row in rows:
            payload.append(row.model_dump(mode="python"))
        self._upsert_dicts(table, payload, key_cols)

    def _upsert_dicts(
        self, table: str, rows: list[dict[str, Any]], key_cols: tuple[str, ...]
    ) -> None:
        if not rows:
            return

        # Map model field names → DB column names
        col_map = _COLUMN_MAP.get(table, {})
        has_col_map = bool(col_map)

        # Deduplicate on model field names (before col mapping)
        # key_cols use DB column names — convert to model field names for dedup
        reverse_map = {v: k for k, v in col_map.items()}
        dedup_key_cols = tuple(reverse_map.get(col, col) for col in key_cols)
        seen: set[tuple] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            key = tuple(row.get(col) for col in dedup_key_cols)
            if key not in seen:
                seen.add(key)
                deduped.append(row)

        # Build DB rows with correct column names
        db_rows: list[dict[str, Any]] = []
        for row in deduped:
            if has_col_map:
                # Models: map model field names → DB column names
                mapped: dict[str, Any] = {}
                for model_field, value in row.items():
                    db_col = col_map.get(model_field, model_field)
                    if db_col is not None:
                        mapped[db_col] = value
            else:
                # Raw records: already DB column names, pass through
                mapped = dict(row)
            # Apply defaults
            for col, default in _DEFAULTS.get(table, {}).items():
                if col not in mapped:
                    mapped[col] = default() if callable(default) else default
            # Fill timestamps only for rows that already have these columns
            if "created_at" in mapped:
                if mapped["created_at"] is None or mapped["created_at"] == "":
                    mapped["created_at"] = _now()
            if "updated_at" in mapped:
                if mapped["updated_at"] is None or mapped["updated_at"] == "":
                    mapped["updated_at"] = _now()
            db_rows.append(mapped)

        if not db_rows:
            return

        columns = list(db_rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(columns)

        conn = self.connect()
        for row in db_rows:
            vals = [row[col] for col in columns]
            conn.execute(
                f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})", vals
            )
        conn.commit()
        conn.commit()
