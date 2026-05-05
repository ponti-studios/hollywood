"""Compatibility shim for the canonical evaluation schema.

Prefer `nexus.evaluation.schema` for new code.
"""

from nexus.evaluation.schema import EvaluationSchema, EvaluationSubjectType

__all__ = ["EvaluationSchema", "EvaluationSubjectType"]
