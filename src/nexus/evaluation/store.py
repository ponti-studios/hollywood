from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from nexus.evaluation.schema import EvaluationSchema


class EvaluationStore:
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
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    benchmark_id TEXT,
                    scorer TEXT NOT NULL,
                    rubric TEXT,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    judgment TEXT,
                    notes TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_subject ON evaluations (subject_type, subject_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_benchmark ON evaluations (benchmark_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_capability ON evaluations (capability)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_created ON evaluations (created_at)")

    def save(self, record: EvaluationSchema) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO evaluations (
                    id, subject_type, subject_id, capability, benchmark_id,
                    scorer, rubric, metrics_json, judgment, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.subject_type,
                    record.subject_id,
                    record.capability,
                    record.benchmark_id,
                    record.scorer,
                    record.rubric,
                    json.dumps(record.metrics),
                    record.judgment,
                    record.notes,
                    record.created_at,
                ),
            )

    def get(self, evaluation_id: str) -> EvaluationSchema | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM evaluations WHERE id = ?", (evaluation_id,)).fetchone()
        return _row_to_evaluation(row) if row else None

    def list(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        benchmark_id: str | None = None,
        capability: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EvaluationSchema]:
        query = "SELECT * FROM evaluations"
        conditions: list[str] = []
        params: list[object] = []

        if subject_type:
            conditions.append("subject_type = ?")
            params.append(subject_type)
        if subject_id:
            conditions.append("subject_id = ?")
            params.append(subject_id)
        if benchmark_id:
            conditions.append("benchmark_id = ?")
            params.append(benchmark_id)
        if capability:
            conditions.append("capability = ?")
            params.append(capability)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_evaluation(row) for row in rows]

    def delete(self, evaluation_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute("DELETE FROM evaluations WHERE id = ?", (evaluation_id,))
        return result.rowcount > 0


def _row_to_evaluation(row: sqlite3.Row) -> EvaluationSchema:
    return EvaluationSchema(
        id=row["id"],
        subject_type=row["subject_type"],
        subject_id=row["subject_id"],
        capability=row["capability"],
        benchmark_id=row["benchmark_id"],
        scorer=row["scorer"],
        rubric=row["rubric"],
        metrics=json.loads(row["metrics_json"]),
        judgment=row["judgment"],
        notes=row["notes"],
        created_at=row["created_at"],
    )
