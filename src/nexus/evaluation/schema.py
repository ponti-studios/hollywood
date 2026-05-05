"""Canonical evaluation schema for Nexus.

Evaluations are measurement objects. They record how a subject was scored, with
what rubric or scorer, and what the resulting quality signals were.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Evaluations can be attached to execution records, assets, models, or experiments.
type EvaluationSubjectType = Literal["run", "model", "artifact", "experiment"]


class EvaluationSchema(BaseModel):
    """Canonical schema for a Nexus evaluation record."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable evaluation ID.")
    subject_type: EvaluationSubjectType = Field(
        description="What kind of thing is being evaluated: run, model, artifact, or experiment.",
    )
    subject_id: str = Field(description="ID of the thing being evaluated.")
    capability: str = Field(description="Primary capability being scored.")
    benchmark_id: str | None = Field(
        default=None,
        description="Benchmark ID when the evaluation is tied to a standard test.",
    )
    scorer: str = Field(
        description="Scorer identity, such as a metric function, judge model, or reviewer label.",
    )
    rubric: str | None = Field(
        default=None,
        description="Rubric or policy reference used for scoring.",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured score payload.",
    )
    judgment: str | None = Field(
        default=None,
        description="Optional qualitative judgment or classification.",
    )
    notes: str | None = Field(
        default=None,
        description="Optional reviewer or system notes.",
    )
    created_at: float = Field(description="Evaluation creation timestamp.")
