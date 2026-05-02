"""
nexus — multimodal inference, training, and evaluation platform.

Package layout
──────────────
  nexus.api        — Nexus control-plane app and transport routers
  nexus.config     — Pydantic models for configs and recipes
  nexus.device     — Apple Silicon / MPS detection and memory utilities
  nexus.data       — Dataset loading, formatting, and collation
  nexus.models     — Model loading and adapter management
  nexus.trainers   — Training workflows and recipe execution
  nexus.evaluation — Metrics and LLM-as-judge evaluation
  nexus.experiments — Benchmark orchestration and run tracking
  nexus.voice      — Voice domain services, paths, and request models
  nexus.cli        — Typer CLI entry points
"""

__version__ = "0.1.0"
