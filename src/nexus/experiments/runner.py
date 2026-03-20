"""
runner.py — Base class for all benchmark experiments.

Design philosophy
──────────────────
Every experiment in this project follows the same lifecycle:

  1. Load config from YAML
  2. Initialize model(s)
  3. Run questions through the model
  4. Score each answer
  5. Log results to W&B + local JSON

The BaseRunner handles steps 1, 2, and 5 — the plumbing that every
experiment shares. Each specific experiment (exp_01, exp_02, exp_03)
subclasses BaseRunner and implements its own run() method.

This prevents copy-pasting boilerplate across experiments and ensures
results are always saved in a consistent format that can be compared
in the W&B dashboard.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table

from nexus.experiments.config import ExperimentConfig, ModelSpec
from nexus.experiments.scoring import BenchmarkScore, QuestionResult

logger = logging.getLogger(__name__)
console = Console()


class BaseRunner(ABC):
    """Abstract base class for all experiment runners.

    Subclass this and implement run(). Everything else — model loading,
    inference, logging, progress tracking — is handled here.

    Example:
        class MyExperiment(BaseRunner):
            def run(self) -> dict[str, BenchmarkScore]:
                results = []
                for question in self.questions:
                    answer = self.generate(self.small_model_pipeline, question)
                    ...
                return scores
    """

    def __init__(self, cfg: ExperimentConfig) -> None:
        self.cfg = cfg
        self._pipelines: dict[str, Any] = {}   # model_id → HuggingFace pipeline
        self._wandb_run: Any = None

        console.rule(f"[bold]{cfg.name}[/bold]")
        console.print(f"[dim]{cfg.description}[/dim]\n")

    # ──────────────────────────────────────────────────────────────────────
    # Model loading
    # ──────────────────────────────────────────────────────────────────────

    def load_models(self) -> None:
        """Load all models specified in the config.

        Models are cached in self._pipelines keyed by model_id.
        This method is called once at the start of an experiment run.
        """
        for spec in self.cfg.models:
            console.print(f"Loading [cyan]{spec.model_id}[/cyan] ({spec.role}) …")
            self._pipelines[spec.model_id] = self._build_pipeline(spec)
        console.print()

    def _build_pipeline(self, spec: ModelSpec) -> Any:
        """Build a text-generation pipeline for a given ModelSpec.

        Uses HuggingFace's pipeline() abstraction which handles tokenization,
        device placement, and batched generation in one call.

        temperature=0.0 gives greedy (deterministic) decoding, which is what
        we want for benchmarking — we don't want randomness to affect scores.
        """
        device = self._get_device()

        if spec.inference_backend == "mlx":
            return self._build_mlx_pipeline(spec)

        import torch
        from transformers import GenerationConfig, pipeline

        pipe = pipeline(
            "text-generation",
            model=spec.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        # Build a GenerationConfig and attach it to the model so we don't mix
        # the deprecated "pass both generation_config and kwargs" pattern.
        # temperature=0 → greedy decoding (do_sample=False, no temperature).
        greedy = spec.temperature == 0.0
        pipe.model.generation_config = GenerationConfig(
            max_new_tokens=spec.max_new_tokens,
            do_sample=not greedy,
            temperature=None if greedy else spec.temperature,
            pad_token_id=pipe.tokenizer.eos_token_id,
        )
        # Signal to generate() that no extra kwargs are needed
        pipe._gen_kwargs = {}
        return pipe

    def _build_mlx_pipeline(self, spec: ModelSpec) -> Any:
        """Build an MLX-based pipeline for Apple Silicon inference.

        MLX is Apple's ML framework — it runs natively on the Neural Engine
        and is significantly faster than PyTorch on Mac for inference.
        Falls back to transformers pipeline if mlx-lm is not installed.
        """
        try:
            from mlx_lm import load, generate

            model, tokenizer = load(spec.model_id)

            class MLXPipeline:
                def __init__(self, m: Any, t: Any, s: ModelSpec) -> None:
                    self.model = m
                    self.tokenizer = t
                    self.spec = s
                    self._gen_kwargs = {"max_tokens": s.max_new_tokens}

                def __call__(self, prompt: str) -> list[dict]:
                    out = generate(self.model, self.tokenizer, prompt=prompt, **self._gen_kwargs)
                    return [{"generated_text": prompt + out}]

            return MLXPipeline(model, tokenizer, spec)
        except ImportError:
            logger.warning("mlx-lm not installed — falling back to transformers pipeline")
            spec_copy = spec.model_copy(update={"inference_backend": "transformers"})
            return self._build_pipeline(spec_copy)

    def _get_device(self) -> str:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    # ──────────────────────────────────────────────────────────────────────
    # Inference
    # ──────────────────────────────────────────────────────────────────────

    def generate(self, model_id: str, prompt: str) -> str:
        """Run a single prompt through a model and return the generated text.

        Generation parameters come from the GenerationConfig attached to the
        model at pipeline-build time — we don't pass any extra kwargs here,
        which avoids the deprecated "pass both generation_config and kwargs"
        warning from newer versions of transformers.

        Returns only the new tokens — the model's response — not the prompt.
        """
        pipe = self._pipelines[model_id]
        # Pass no generation kwargs — all params are in model.generation_config
        outputs = pipe(prompt)
        full_text: str = outputs[0]["generated_text"]
        response = full_text[len(prompt):].strip()
        return response

    # ──────────────────────────────────────────────────────────────────────
    # Progress tracking
    # ──────────────────────────────────────────────────────────────────────

    def progress_bar(self, total: int, description: str) -> Progress:
        """Create a Rich progress bar for iterating over questions."""
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────────────────────────────

    def init_wandb(self) -> None:
        """Initialize a Weights & Biases run for experiment tracking.

        W&B stores every run permanently and lets you compare experiments
        in a browser dashboard. If W&B is not configured or the project is
        None in the config, this is a no-op.
        """
        if self.cfg.logging.wandb_project is None:
            return
        try:
            import wandb
            self._wandb_run = wandb.init(
                project=self.cfg.logging.wandb_project,
                name=self.cfg.name,
                config=self.cfg.model_dump(),
                tags=[f"phase-{self.cfg.phase}"],
            )
            console.print(f"W&B run: [link]{self._wandb_run.url}[/link]")
        except ImportError:
            logger.warning("wandb not installed — skipping experiment tracking")

    def log_scores(self, scores: dict[str, BenchmarkScore]) -> None:
        """Log aggregate scores to W&B and the local console."""
        if self._wandb_run is not None:
            import wandb
            flat = {}
            for key, score in scores.items():
                for k, v in score.to_dict().items():
                    if v is not None:
                        flat[f"{key}/{k}"] = v
            wandb.log(flat)

    def save_results(
        self,
        scores: dict[str, BenchmarkScore],
        results: Optional[list[QuestionResult]] = None,
    ) -> Path:
        """Write scores (and optionally full transcripts) to disk as JSON.

        The output file is always written, even if W&B is unavailable.
        This ensures you always have a local record of every run.
        """
        out_dir = self.cfg.output_path()
        timestamp = int(time.time())

        # Scores summary
        scores_path = out_dir / f"scores_{timestamp}.json"
        with open(scores_path, "w") as f:
            json.dump({k: v.to_dict() for k, v in scores.items()}, f, indent=2)
        console.print(f"Scores saved → [cyan]{scores_path}[/cyan]")

        # Full transcripts (question + model answer + correct/incorrect)
        if results and self.cfg.logging.save_transcripts:
            transcripts_path = out_dir / f"transcripts_{timestamp}.json"
            with open(transcripts_path, "w") as f:
                json.dump(
                    [
                        {
                            "id": r.question_id,
                            "question": r.question,
                            "expected": r.expected,
                            "predicted": r.predicted,
                            "correct": r.correct,
                            "model": r.model_id,
                            "benchmark": r.benchmark,
                            "tool_calls": r.tool_calls,
                            "draft": r.draft,
                            "critique": r.critique,
                        }
                        for r in results
                    ],
                    f,
                    indent=2,
                )
            console.print(f"Transcripts saved → [cyan]{transcripts_path}[/cyan]")

        return out_dir

    def print_summary_table(self, scores: dict[str, BenchmarkScore]) -> None:
        """Print a formatted results table to the terminal."""
        table = Table(title=f"Results: {self.cfg.name}", show_lines=True)
        table.add_column("Model", style="cyan")
        table.add_column("Benchmark", style="magenta")
        table.add_column("Accuracy", justify="right", style="bold green")
        table.add_column("Correct / Total", justify="right")
        table.add_column("Tool Call Rate", justify="right")
        table.add_column("Δ Correction", justify="right")

        for key, score in scores.items():
            delta = f"{score.correction_delta:+.1f}pp" if score.correction_delta is not None else "—"
            tool_rate = f"{score.tool_call_rate * 100:.0f}%" if score.tool_call_rate > 0 else "—"
            table.add_row(
                score.model_id.split("/")[-1],
                score.benchmark,
                score.accuracy_pct,
                f"{score.correct_count} / {score.total}",
                tool_rate,
                delta,
            )
        console.print(table)

    # ──────────────────────────────────────────────────────────────────────
    # Entry point
    # ──────────────────────────────────────────────────────────────────────

    def execute(self) -> dict[str, BenchmarkScore]:
        """Top-level entry point — load models, run experiment, save results.

        Call this instead of run() directly. It handles the full lifecycle:
        model loading → W&B init → run → save → print summary → W&B finish.
        """
        self.load_models()
        self.init_wandb()

        try:
            scores, all_results = self.run()
        finally:
            if self._wandb_run is not None:
                import wandb
                wandb.finish()

        self.log_scores(scores)
        self.save_results(scores, all_results)
        self.print_summary_table(scores)
        return scores

    @abstractmethod
    def run(self) -> tuple[dict[str, BenchmarkScore], list[QuestionResult]]:
        """Run the experiment and return (scores_dict, all_results).

        scores_dict: maps a descriptive key (e.g. "small/triviaqa") to a BenchmarkScore
        all_results: flat list of every QuestionResult, used for transcript saving
        """
        ...
