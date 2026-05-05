"""Compatibility re-export layer for Nexus schema models.

Canonical schemas now live in their owning packages:

- `nexus.runs.schema`
- `nexus.evaluation.schema`
- `nexus.experiments.schema`
- `nexus.jobs.schema`
- `nexus.artifacts.schema`

Import from those owning packages when adding new code. Keep `nexus.schemas`
only as a facade for compatibility and ergonomic imports.
"""

from nexus.artifacts.schema import ArtifactKind, ArtifactSchema
from nexus.evaluation.schema import EvaluationSchema, EvaluationSubjectType
from nexus.experiments.schema import ExperimentSchema, ExperimentStatus, ExperimentVariantSchema
from nexus.jobs.schema import JobKind, JobSchema, JobStatus
from nexus.runs.schema import RunKind, RunSchema, RunStatus

__all__ = [
    "ArtifactKind",
    "ArtifactSchema",
    "EvaluationSchema",
    "EvaluationSubjectType",
    "ExperimentSchema",
    "ExperimentStatus",
    "ExperimentVariantSchema",
    "JobKind",
    "JobSchema",
    "JobStatus",
    "RunKind",
    "RunSchema",
    "RunStatus",
]
