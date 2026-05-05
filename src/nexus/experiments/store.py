from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from nexus.experiments.schema import ExperimentSchema, ExperimentVariantSchema


class ExperimentStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL,
                    benchmark_ids_json TEXT NOT NULL DEFAULT '[]',
                    variant_specs_json TEXT NOT NULL DEFAULT '[]',
                    run_ids_json TEXT NOT NULL DEFAULT '[]',
                    evaluation_ids_json TEXT NOT NULL DEFAULT '[]',
                    config_json TEXT NOT NULL DEFAULT '{}',
                    summary_json TEXT,
                    winner TEXT,
                    error_json TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_capability ON experiments (capability)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments (created_at)")

    def save(self, record: ExperimentSchema) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO experiments (
                    id, name, hypothesis, capability, status,
                    benchmark_ids_json, variant_specs_json, run_ids_json, evaluation_ids_json,
                    config_json, summary_json, winner, error_json,
                    created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.name,
                    record.hypothesis,
                    record.capability,
                    record.status,
                    json.dumps(record.benchmark_ids),
                    json.dumps([variant.model_dump(mode="json") for variant in record.variant_specs]),
                    json.dumps(record.run_ids),
                    json.dumps(record.evaluation_ids),
                    json.dumps(record.config),
                    _json_dumps(record.summary),
                    record.winner,
                    _json_dumps(record.error),
                    record.created_at,
                    record.started_at,
                    record.completed_at,
                ),
            )

    def get(self, experiment_id: str) -> ExperimentSchema | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
        return _row_to_experiment(row) if row else None

    def list(
        self,
        *,
        capability: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExperimentSchema]:
        query = "SELECT * FROM experiments"
        conditions: list[str] = []
        params: list[object] = []

        if capability:
            conditions.append("capability = ?")
            params.append(capability)
        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_experiment(row) for row in rows]

    def delete(self, experiment_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
        return result.rowcount > 0


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _json_loads(value: str | None):
    if value is None:
        return None
    return json.loads(value)


def _row_to_experiment(row: sqlite3.Row) -> ExperimentSchema:
    return ExperimentSchema(
        id=row["id"],
        name=row["name"],
        hypothesis=row["hypothesis"],
        capability=row["capability"],
        status=row["status"],
        benchmark_ids=_json_loads(row["benchmark_ids_json"]) or [],
        variant_specs=[
            ExperimentVariantSchema.model_validate(item)
            for item in (_json_loads(row["variant_specs_json"]) or [])
        ],
        run_ids=_json_loads(row["run_ids_json"]) or [],
        evaluation_ids=_json_loads(row["evaluation_ids_json"]) or [],
        config=_json_loads(row["config_json"]) or {},
        summary=_json_loads(row["summary_json"]),
        winner=row["winner"],
        error=_json_loads(row["error_json"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )
