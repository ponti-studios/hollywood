"""Compatibility shim for the canonical run schema.

Prefer `nexus.runs.schema` for new code.
"""

from nexus.runs.schema import RunKind, RunSchema, RunStatus

__all__ = ["RunKind", "RunSchema", "RunStatus"]
