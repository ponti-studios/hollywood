"""Compatibility shim for the canonical job schema.

Prefer `nexus.jobs.schema` for new code.
"""

from nexus.jobs.schema import JobKind, JobSchema, JobStatus

__all__ = ["JobKind", "JobSchema", "JobStatus"]
