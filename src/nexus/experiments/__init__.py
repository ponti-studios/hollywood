"""
Experiment orchestration for Nexus benchmark and comparison runs.

This package provides the scaffolding to run, score, and log the benchmark
phases used to evaluate Gemma 4 E2B-it and any approved local checkpoints:

  Phase 1 (exp_01): Baseline — closed-book evaluation
  Phase 2 (exp_02): Open Book — tool-assisted evaluation
  Phase 3 (exp_03): Reflection — Draft → Critique → Refine loop

Every experiment follows the same contract:
  - Reads a YAML config (ExperimentConfig)
  - Inherits from BaseRunner
  - Logs results to W&B and a local JSON file
"""

from nexus.experiments.config import ExperimentConfig
from nexus.experiments.runner import BaseRunner
from nexus.experiments.schema import ExperimentSchema, ExperimentStatus, ExperimentVariantSchema
from nexus.experiments.store import ExperimentStore

__all__ = [
    "BaseRunner",
    "ExperimentConfig",
    "ExperimentSchema",
    "ExperimentStatus",
    "ExperimentStore",
    "ExperimentVariantSchema",
]
