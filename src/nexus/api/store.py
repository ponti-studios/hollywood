from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InferenceRecord:
    id: str
    created_at: float
    model_id: str
    messages: list[dict]
    response: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "messages": self.messages,
            "response": self.response,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
        }


class InferenceStore:
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inference_runs (
                    id               TEXT PRIMARY KEY,
                    created_at       REAL NOT NULL,
                    model_id         TEXT NOT NULL,
                    messages         TEXT NOT NULL,
                    response         TEXT NOT NULL,
                    prompt_tokens    INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    latency_ms       REAL NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON inference_runs (model_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON inference_runs (created_at)")

    def save(self, record: InferenceRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO inference_runs
                   (id, created_at, model_id, messages, response, prompt_tokens, completion_tokens, latency_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.created_at,
                    record.model_id,
                    json.dumps(record.messages),
                    record.response,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.latency_ms,
                ),
            )

    def get(self, run_id: str) -> InferenceRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM inference_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return _row_to_record(row) if row else None

    def list(
        self,
        model_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InferenceRecord]:
        query = "SELECT * FROM inference_runs"
        params: list = []
        if model_id:
            query += " WHERE model_id = ?"
            params.append(model_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def delete(self, run_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM inference_runs WHERE id = ?", (run_id,)
            )
        return result.rowcount > 0


def _row_to_record(row: sqlite3.Row) -> InferenceRecord:
    return InferenceRecord(
        id=row["id"],
        created_at=row["created_at"],
        model_id=row["model_id"],
        messages=json.loads(row["messages"]),
        response=row["response"],
        prompt_tokens=row["prompt_tokens"],
        completion_tokens=row["completion_tokens"],
        latency_ms=row["latency_ms"],
    )
