from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from nexus.runs.schema import RunKind, RunStatus


@dataclass
class RunRecord:
    id: str
    kind: RunKind
    capability: str
    status: RunStatus
    created_at: float
    model_id: str | None = None
    job_id: str | None = None
    experiment_id: str | None = None
    evaluation_id: str | None = None
    benchmark_id: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    artifact_ids: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    started_at: float | None = None
    completed_at: float | None = None

    @classmethod
    def inference(
        cls,
        *,
        id: str,
        model_id: str,
        messages: list[dict[str, Any]],
        response: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        created_at: float | None = None,
        capability: str = "text",
        config: dict[str, Any] | None = None,
    ) -> RunRecord:
        completed_at = created_at if created_at is not None else time.time()
        started_at = completed_at - (latency_ms / 1000)
        return cls(
            id=id,
            kind="inference",
            capability=capability,
            status="completed",
            model_id=model_id,
            input={"messages": messages},
            output={"response": response},
            config=config or {},
            metrics={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            artifact_ids=[],
            error=None,
            started_at=started_at,
            completed_at=completed_at,
            created_at=completed_at,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "capability": self.capability,
            "status": self.status,
            "model_id": self.model_id,
            "job_id": self.job_id,
            "experiment_id": self.experiment_id,
            "evaluation_id": self.evaluation_id,
            "benchmark_id": self.benchmark_id,
            "input": self.input,
            "output": self.output,
            "config": self.config,
            "metrics": self.metrics,
            "artifact_ids": self.artifact_ids,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
        }

        if self.kind == "inference":
            if self.input and "messages" in self.input:
                data["messages"] = self.input["messages"]
            if self.output and "response" in self.output:
                data["response"] = self.output["response"]
            if self.metrics:
                data["prompt_tokens"] = self.metrics.get("prompt_tokens")
                data["completion_tokens"] = self.metrics.get("completion_tokens")
                data["latency_ms"] = self.metrics.get("latency_ms")

        return data
