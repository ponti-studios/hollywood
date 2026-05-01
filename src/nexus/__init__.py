"""
nexus — Gemma 3 posttraining lab for Apple Silicon.

Package layout
──────────────
  nexus.config     — Pydantic models for all YAML configs (Recipe, ModelConfig, …)
  nexus.device     — Apple Silicon / MPS detection and memory utilities
  nexus.data       — Dataset loading, formatting, and collation
  nexus.models     — Model loading and LoRA adapter management
  nexus.trainers   — SFT, DPO, ORPO, GRPO training loops
  nexus.evaluation — Metrics and LLM-as-judge evaluation
  nexus.voice      — Voice domain services, paths, and request models
  nexus.cli        — Typer CLI entry points
"""

__version__ = "0.1.0"
