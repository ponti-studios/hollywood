"""Compatibility shim for the canonical artifact schema.

Prefer `nexus.artifacts.schema` for new code.
"""

from nexus.artifacts.schema import ArtifactKind, ArtifactSchema

__all__ = ["ArtifactKind", "ArtifactSchema"]
