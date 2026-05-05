from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nexus.runs import RunRecord, RunStore


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

    def to_run_record(self, *, capability: str = "text") -> RunRecord:
        return RunRecord.inference(
            id=self.id,
            model_id=self.model_id,
            messages=self.messages,
            response=self.response,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            latency_ms=self.latency_ms,
            created_at=self.created_at,
            capability=capability,
        )

    @classmethod
    def from_run_record(cls, record: RunRecord) -> InferenceRecord:
        messages = []
        if record.input and isinstance(record.input.get("messages"), list):
            messages = record.input["messages"]

        response = ""
        if record.output and isinstance(record.output.get("response"), str):
            response = record.output["response"]

        metrics = record.metrics or {}
        return cls(
            id=record.id,
            created_at=record.created_at,
            model_id=record.model_id or "",
            messages=messages,
            response=response,
            prompt_tokens=int(metrics.get("prompt_tokens", 0)),
            completion_tokens=int(metrics.get("completion_tokens", 0)),
            latency_ms=float(metrics.get("latency_ms", 0.0)),
        )


class InferenceStore:
    """Compatibility shim over the platform RunStore.

    Existing scripts and tests still use inference-specific records while the
    API moves toward a platform-wide run ledger.
    """

    def __init__(self, db_path: Path) -> None:
        self._run_store = RunStore(db_path)

    def save(self, record: InferenceRecord) -> None:
        self._run_store.save(record.to_run_record())

    def get(self, run_id: str) -> InferenceRecord | None:
        record = self._run_store.get(run_id)
        if record is None:
            return None
        return InferenceRecord.from_run_record(record)

    def list(
        self,
        model_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InferenceRecord]:
        records = self._run_store.list(
            kind="inference",
            model_id=model_id,
            limit=limit,
            offset=offset,
        )
        return [InferenceRecord.from_run_record(record) for record in records]

    def delete(self, run_id: str) -> bool:
        return self._run_store.delete(run_id)
