"""Canonical artifact schema for Nexus.

Artifacts are durable outputs produced by runs and jobs. They are the memory of
the platform: generated media, checkpoints, reports, transcripts, and more.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Artifact kinds capture durable output classes across capabilities.
type ArtifactKind = Literal["model", "audio", "image", "transcript", "report", "dataset_export", "other"]


class ArtifactSchema(BaseModel):
    """Canonical schema for a durable Nexus artifact."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable artifact ID.")
    kind: ArtifactKind = Field(description="Artifact class, such as audio or report.")
    capability: str | None = Field(
        default=None,
        description="Primary capability when the artifact belongs to one.",
    )
    producer_run_id: str | None = Field(
        default=None,
        description="Run that produced the artifact.",
    )
    producer_job_id: str | None = Field(
        default=None,
        description="Job that produced the artifact.",
    )
    uri: str = Field(description="Storage location or local path.")
    media_type: str | None = Field(
        default=None,
        description="MIME type or equivalent media classification.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Artifact-specific metadata payload.",
    )
    checksum: str | None = Field(
        default=None,
        description="Optional integrity checksum.",
    )
    created_at: float = Field(description="Artifact creation timestamp.")
