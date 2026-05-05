"""Canonical experiment schema for Nexus.

Experiments are comparison objects. They organize hypothesis-driven work across
variants, runs, evaluations, and benchmarks.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Experiments track lifecycle just like other long-running platform objects.
type ExperimentStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class ExperimentVariantSchema(BaseModel):
    """A single variant being compared in an experiment."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable variant ID inside the experiment.")
    model_id: str | None = Field(
        default=None,
        description="Primary model associated with the variant.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Variant-specific configuration such as prompt, decoding, or tool settings.",
    )


class ExperimentSchema(BaseModel):
    """Canonical schema for a structured comparison in Nexus."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable experiment ID.")
    name: str = Field(description="Human-readable experiment name.")
    hypothesis: str = Field(description="Question or claim the experiment is testing.")
    capability: str = Field(description="Primary capability under study.")
    status: ExperimentStatus = Field(description="Lifecycle state for the experiment.")
    benchmark_ids: list[str] = Field(
        default_factory=list,
        description="Benchmarks used by the experiment.",
    )
    variant_specs: list[ExperimentVariantSchema] = Field(
        default_factory=list,
        description="Variants being compared in the experiment.",
    )
    run_ids: list[str] = Field(
        default_factory=list,
        description="Runs belonging to the experiment.",
    )
    evaluation_ids: list[str] = Field(
        default_factory=list,
        description="Evaluations attached to the experiment.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Submitted experiment config snapshot.",
    )
    summary: dict[str, Any] | None = Field(
        default=None,
        description="Structured summary of the comparison outcome.",
    )
    winner: str | None = Field(
        default=None,
        description="Winning variant ID or recommendation, when one exists.",
    )
    error: dict[str, Any] | None = Field(
        default=None,
        description="Structured error payload when the experiment fails.",
    )
    created_at: float = Field(description="Creation timestamp.")
    started_at: float | None = Field(default=None, description="Execution start timestamp.")
    completed_at: float | None = Field(default=None, description="Execution completion timestamp.")
