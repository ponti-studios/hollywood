"""
config.py — Pydantic configuration models for benchmark experiments.

Why separate experiment configs from training configs?
──────────────────────────────────────────────────────
Training configs (Recipe in nexus.config) control *how a model learns*.
Experiment configs control *how a model is evaluated*. These are different
concerns: an experiment might compare a fine-tuned checkpoint against a
baseline, or test two models on three different datasets simultaneously.

Keeping them separate also means you can re-run the same experiment on a new
model checkpoint by changing one line in the YAML — no code changes needed.

Usage:
    cfg = ExperimentConfig.from_yaml("configs/benchmarks/exp_01.yaml")
    runner = BaselineRunner(cfg)
    runner.run()
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ModelSpec(BaseModel):
    """Specifies a model to load during an experiment.

    model_id: HuggingFace repo name, e.g. "google/gemma-4-e2b"
              Can also be a local path to a fine-tuned checkpoint.

    role: "small" = the 3B model under test
          "large" = the reference model we're comparing against (optional)
          "judge" = a model used to score outputs (Phase 3+)

        inference_backend: how to run the model.
            "transformers"      — standard HuggingFace pipeline. Slowest, most flexible.
            "openai-compatible" — remote chat-completions API compatible with OpenAI's schema.
    """

    model_id: str
    role: Literal["small", "large", "judge"] = "small"
    inference_backend: Literal["transformers", "openai-compatible"] = "transformers"
    max_new_tokens: int = 256
    temperature: float = 0.0   # 0.0 = greedy decoding (fully deterministic)
    batch_size: int = 8
    api_base: str | None = None
    api_key_env: str | None = None
    request_timeout_seconds: float = 120.0


class BenchmarkSpec(BaseModel):
    """Which benchmark dataset(s) to run in this experiment.

    name: shorthand identifier.
      "triviaqa"  — open-domain trivia questions (knowledge-heavy)
      "mmlu"      — 57-subject academic knowledge (knowledge-heavy)
      "synthetic" — procedurally generated logic puzzles (zero-knowledge)

    samples: how many questions to evaluate. None = the full dataset.
             500 is a good balance of statistical validity and runtime.

    seed: fixed seed so the same questions are sampled every time you run.
          Changing the seed gives a different random sample of the same split,
          which is useful for measuring variance across runs.

    mmlu_subjects: which MMLU subject categories to include. None = all 57.
                   For quick experiments, pick 3–5 subjects.
    """

    name: Literal["triviaqa", "mmlu", "synthetic"]
    samples: int | None = 500
    seed: int = 42
    mmlu_subjects: list[str] | None = None  # None = all subjects


class SyntheticPuzzleSpec(BaseModel):
    """Controls the procedurally-generated logic puzzle generator.

    This generator creates puzzles using nonsense words so the model cannot
    pattern-match to training data. Every run with the same seed produces
    the same puzzles, ensuring reproducibility.

    depth_range: (min, max) number of reasoning steps per puzzle.
                 depth=2 → "All A are B. All B are C. Is X a C?"
                 depth=4 → a four-step syllogism chain

    puzzle_types: which logical structures to generate.
      "syllogism"   — All A are B style chains
      "conditional" — If A then B, given A, conclude B (modus ponens)
      "negation"    — None of A are B, is X a B?
    """

    depth_range: tuple[int, int] = (2, 4)
    puzzle_types: list[Literal["syllogism", "conditional", "negation"]] = [
        "syllogism", "conditional", "negation"
    ]
    vocab_size: int = 200   # how many nonsense words to draw from


class LoggingSpec(BaseModel):
    """Where to send results.

    wandb_project: the W&B project that groups all logic-broker runs.
                   Leave as None to skip W&B logging (useful for offline dev).

    output_dir: local directory for JSON result files.
                Results are always written locally, regardless of W&B status.
    """

    wandb_project: str | None = "3b-logic-broker"
    output_dir: str = ".data/benchmarks/results"
    save_transcripts: bool = True   # save full question/answer pairs, not just scores
    reference_cache_dir: str = ".data/benchmarks/cache"
    use_reference_cache: bool = True
    refresh_reference_cache: bool = False
    reference_cache_warn_after_hours: int = 168


class ExperimentConfig(BaseModel):
    """A complete experiment definition — ties together models, data, and logging.

    Maps 1:1 to a YAML file in configs/benchmarks/.

    Example usage:
        cfg = ExperimentConfig.from_yaml("configs/benchmarks/exp_01.yaml")
    """

    name: str
    description: str = ""
    phase: Literal[1, 2, 3, 4] = 1

    models: list[ModelSpec] = Field(default_factory=list)
    benchmarks: list[BenchmarkSpec] = Field(default_factory=list)
    synthetic: SyntheticPuzzleSpec = Field(default_factory=SyntheticPuzzleSpec)
    logging: LoggingSpec = Field(default_factory=LoggingSpec)

    @classmethod
    def from_yaml(cls, path: str | Path) -> ExperimentConfig:
        """Load and validate an experiment config from a YAML file."""
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls(**raw)

    @property
    def small_model(self) -> ModelSpec | None:
        """Return the ModelSpec with role='small', or None if not configured."""
        return next((m for m in self.models if m.role == "small"), None)

    @property
    def large_model(self) -> ModelSpec | None:
        """Return the ModelSpec with role='large', or None if not configured."""
        return next((m for m in self.models if m.role == "large"), None)

    def output_path(self) -> Path:
        """Resolve the output directory, creating it if necessary."""
        path = Path(self.logging.output_dir) / self.name
        path.mkdir(parents=True, exist_ok=True)
        return path
