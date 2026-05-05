"""Compatibility shim for the canonical experiment schema.

Prefer `nexus.experiments.schema` for new code.
"""

from nexus.experiments.schema import ExperimentSchema, ExperimentStatus, ExperimentVariantSchema

__all__ = ["ExperimentSchema", "ExperimentStatus", "ExperimentVariantSchema"]
