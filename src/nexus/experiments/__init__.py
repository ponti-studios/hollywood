"""
experiments/ — Controlled benchmark experiments for the 3B Logic Broker project.

This package provides the scaffolding to run, score, and log all four phases
of the procedural intelligence hypothesis:

  Phase 1 (exp_01): Baseline — 3B vs 70B on knowledge vs pure logic
  Phase 2 (exp_02): Open Book — 3B + tool-use vs 70B on knowledge tasks
  Phase 3 (exp_03): Reflection — Draft → Critique → Refine loop
  Phase 4 (exp_04): Fine-tuned 3B vs zero-shot frontier models

Every experiment follows the same contract:
  - Reads a YAML config (ExperimentConfig)
  - Inherits from BaseRunner
  - Logs results to W&B and a local JSON file
"""

from nexus.experiments.config import ExperimentConfig
from nexus.experiments.runner import BaseRunner

__all__ = ["ExperimentConfig", "BaseRunner"]
