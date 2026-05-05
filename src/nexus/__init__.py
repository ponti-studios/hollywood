"""
nexus — multimodal inference, training, and evaluation platform.

Package layout
──────────────
  nexus.api        — Nexus control-plane app and transport routers
  nexus.config     — Pydantic models for configs and recipes
  nexus.device     — Apple Silicon / MPS detection and memory utilities
  nexus.data       — Dataset loading, formatting, and collation
  nexus.models     — Model loading and adapter management
  nexus.runs       — Platform run records and durable run storage
  nexus.schemas    — Compatibility re-export layer for schema imports
  nexus.text       — Text generation backend service app
  nexus.trainers   — Training workflows and recipe execution
  nexus.evaluation — Evaluation logic, schema, and durable storage
  nexus.experiments — Benchmark orchestration, schema, and durable storage
  nexus.jobs       — Job schema primitives for orchestrated work
  nexus.artifacts  — Artifact schema primitives for durable outputs
  nexus.audio      — Audio domain services (TTS/ASR), paths, and request models
  nexus.cli        — Typer CLI entry points
"""

__version__ = "0.1.0"
