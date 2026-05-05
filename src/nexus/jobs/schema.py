"""Canonical job schema for Nexus.

A job is the orchestration wrapper around work. Jobs exist when lifecycle,
queueing, retries, cancellation, or progress tracking matter.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Job kinds describe the orchestration category, not the low-level executor.
type JobKind = Literal["training", "evaluation", "benchmark", "export", "batch_inference"]

# Job lifecycle states are intentionally queue-oriented.
type JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class JobSchema(BaseModel):
    """Canonical schema for managed work in Nexus."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable job ID.")
    kind: JobKind = Field(description="Job type, such as training or batch_inference.")
    capability: str | None = Field(
        default=None,
        description="Primary capability when the job is associated with one modality.",
    )
    status: JobStatus = Field(description="Lifecycle state for the job.")
    requested_by: str | None = Field(
        default=None,
        description="Actor or system that submitted the job.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Submitted job configuration snapshot.",
    )
    run_ids: list[str] = Field(
        default_factory=list,
        description="Runs created under this job.",
    )
    result_summary: dict[str, Any] | None = Field(
        default=None,
        description="Compact summary of the job outcome.",
    )
    error: dict[str, Any] | None = Field(
        default=None,
        description="Structured failure payload when the job fails.",
    )
    progress: dict[str, Any] | None = Field(
        default=None,
        description="Progress metadata such as step counts or percentages.",
    )
    created_at: float = Field(description="Submission timestamp.")
    started_at: float | None = Field(default=None, description="Execution start timestamp.")
    completed_at: float | None = Field(default=None, description="Execution completion timestamp.")
