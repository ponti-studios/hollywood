from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from nexus.runs.models import RunRecord


class RunStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_schema()
        self._migrate_legacy_inference_runs()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model_id TEXT,
                    job_id TEXT,
                    experiment_id TEXT,
                    evaluation_id TEXT,
                    benchmark_id TEXT,
                    input_json TEXT,
                    output_json TEXT,
                    config_json TEXT,
                    metrics_json TEXT,
                    artifact_ids_json TEXT NOT NULL DEFAULT '[]',
                    error_json TEXT,
                    started_at REAL,
                    completed_at REAL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_kind ON runs (kind)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_capability ON runs (capability)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_model ON runs (model_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON runs (created_at)")

    def _has_table(self, conn: sqlite3.Connection, name: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        return row is not None

    def _migrate_legacy_inference_runs(self) -> None:
        with self._connect() as conn:
            if not self._has_table(conn, "inference_runs"):
                return

            rows = conn.execute(
                "SELECT id, created_at, model_id, messages, response, prompt_tokens, completion_tokens, latency_ms FROM inference_runs"
            ).fetchall()
            if not rows:
                return

            for row in rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO runs (
                        id, kind, capability, status, model_id,
                        input_json, output_json, config_json, metrics_json,
                        artifact_ids_json, error_json,
                        started_at, completed_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        "inference",
                        "text",
                        "completed",
                        row["model_id"],
                        json.dumps({"messages": json.loads(row["messages"])}),
                        json.dumps({"response": row["response"]}),
                        json.dumps({}),
                        json.dumps(
                            {
                                "prompt_tokens": row["prompt_tokens"],
                                "completion_tokens": row["completion_tokens"],
                                "latency_ms": row["latency_ms"],
                                "total_tokens": row["prompt_tokens"] + row["completion_tokens"],
                            }
                        ),
                        json.dumps([]),
                        None,
                        float(row["created_at"]) - (float(row["latency_ms"]) / 1000),
                        float(row["created_at"]),
                        float(row["created_at"]),
                    ),
                )

    def save(self, record: RunRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    id, kind, capability, status, model_id,
                    job_id, experiment_id, evaluation_id, benchmark_id,
                    input_json, output_json, config_json, metrics_json,
                    artifact_ids_json, error_json,
                    started_at, completed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.kind,
                    record.capability,
                    record.status,
                    record.model_id,
                    record.job_id,
                    record.experiment_id,
                    record.evaluation_id,
                    record.benchmark_id,
                    _json_dumps(record.input),
                    _json_dumps(record.output),
                    _json_dumps(record.config),
                    _json_dumps(record.metrics),
                    json.dumps(record.artifact_ids),
                    _json_dumps(record.error),
                    record.started_at,
                    record.completed_at,
                    record.created_at,
                ),
            )

    def get(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None

    def list(
        self,
        *,
        kind: str | None = None,
        capability: str | None = None,
        model_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RunRecord]:
        query = "SELECT * FROM runs"
        conditions: list[str] = []
        params: list[Any] = []

        if kind:
            conditions.append("kind = ?")
            params.append(kind)
        if capability:
            conditions.append("capability = ?")
            params.append(capability)
        if model_id:
            conditions.append("model_id = ?")
            params.append(model_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_run(row) for row in rows]

    def delete(self, run_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        return result.rowcount > 0


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _json_loads(value: str | None) -> Any:
    if value is None:
        return None
    return json.loads(value)


def _row_to_run(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        id=row["id"],
        kind=row["kind"],
        capability=row["capability"],
        status=row["status"],
        model_id=row["model_id"],
        job_id=row["job_id"],
        experiment_id=row["experiment_id"],
        evaluation_id=row["evaluation_id"],
        benchmark_id=row["benchmark_id"],
        input=_json_loads(row["input_json"]),
        output=_json_loads(row["output_json"]),
        config=_json_loads(row["config_json"]),
        metrics=_json_loads(row["metrics_json"]),
        artifact_ids=_json_loads(row["artifact_ids_json"]) or [],
        error=_json_loads(row["error_json"]),
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )
