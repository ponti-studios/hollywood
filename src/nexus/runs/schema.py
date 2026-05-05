"""Canonical run schema for Nexus.

This model is the code-backed contract for a single execution record.
Use it anywhere a run needs to cross a boundary cleanly:

- API responses
- storage serialization
- job orchestration metadata
- experiment membership
- reporting and analytics

The comments and field descriptions here replace prose-only schema docs.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# What kind of work this run represents.
type RunKind = Literal["inference", "training", "evaluation", "benchmark", "experiment_trial"]

# Lifecycle state for the run.
type RunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class RunSchema(BaseModel):
    """Canonical schema for a single Nexus run.

    A run is the atomic execution record in Nexus. Every major workflow should
    be understandable in terms of runs, even if a higher-level job or
    experiment groups them together.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable run ID.")
    kind: RunKind = Field(description="Kind of run, such as inference or training.")
    capability: str = Field(description="Primary capability, such as text, image, or audio.")
    status: RunStatus = Field(description="Lifecycle state for the run.")
    model_id: str | None = Field(default=None, description="Model identifier used by the run.")
    job_id: str | None = Field(default=None, description="Parent job ID when the run belongs to a job.")
    experiment_id: str | None = Field(
        default=None,
        description="Parent experiment ID when the run participates in an experiment.",
    )
    evaluation_id: str | None = Field(
        default=None,
        description="Linked evaluation ID when the run has a primary evaluation record.",
    )
    benchmark_id: str | None = Field(
        default=None,
        description="Benchmark ID when the run is tied to a standard test suite.",
    )
    input: dict[str, Any] | None = Field(
        default=None,
        description="Normalized input payload or reference used for execution.",
    )
    output: dict[str, Any] | None = Field(
        default=None,
        description="Normalized output payload produced by the run.",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Configuration snapshot used to execute the run.",
    )
    metrics: dict[str, Any] | None = Field(
        default=None,
        description="Structured metrics collected during execution.",
    )
    artifact_ids: list[str] = Field(
        default_factory=list,
        description="Artifacts produced by the run.",
    )
    error: dict[str, Any] | None = Field(
        default=None,
        description="Structured error payload when the run fails.",
    )
    started_at: float | None = Field(default=None, description="Execution start timestamp.")
    completed_at: float | None = Field(default=None, description="Execution completion timestamp.")
    created_at: float = Field(description="Record creation timestamp.")
    messages: list[dict[str, Any]] | None = Field(
        default=None,
        description="Legacy-compatible inference input messages.",
    )
    response: str | None = Field(default=None, description="Legacy-compatible inference response text.")
    prompt_tokens: int | None = Field(
        default=None,
        description="Legacy-compatible prompt token count for inference runs.",
    )
    completion_tokens: int | None = Field(
        default=None,
        description="Legacy-compatible completion token count for inference runs.",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Legacy-compatible latency metric for inference runs.",
    )
