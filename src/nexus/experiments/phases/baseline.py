"""
exp_01_baseline.py — Phase 1: The "Category Error" Baseline

What this experiment proves
────────────────────────────
Gemma 4 E2B-it is the single approved text model in this repository. The
baseline compares the model against itself and any approved local Gemma
checkpoint to keep the benchmark and cache machinery honest.

The benchmark suite covers:

  1. TriviaQA  — knowledge-heavy, tests factual recall
  2. MMLU      — knowledge-heavy, tests academic subject knowledge
  3. Synthetic — pure logic, tests reasoning with made-up words

Expected outcome:
  - TriviaQA and MMLU are the hard factual sets
  - Synthetic should remain relatively strong because it is pure reasoning
  - Differences between the sets tell us whether the model is relying on
    memorisation or actually reasoning

If the Synthetic gap grows unexpectedly large, we need to revisit the setup.

Usage:
    python -m nexus.experiments.phases.baseline
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rich.console import Console

from nexus.experiments.benchmarks import mmlu, synthetic, triviaqa
from nexus.experiments.config import BenchmarkSpec, ExperimentConfig, ModelSpec
from nexus.experiments.reference_cache import (
    load_cache_metadata,
    load_reference_cache,
    save_reference_cache,
)
from nexus.experiments.runner import BaseRunner
from nexus.experiments.scoring import (
    BenchmarkScore,
    QuestionResult,
    aggregate_scores,
    score_logic_puzzle,
    score_mmlu,
    score_triviaqa,
)

console = Console()


class BaselineRunner(BaseRunner):
    """Phase 1 runner — evaluates the approved Gemma model on all benchmarks.

    Runs each configured model on each benchmark sequentially and collects
    results. No tools, no reflection — this is the pure "closed book"
    baseline that every subsequent phase will be compared against.
    """

    def run(self) -> tuple[dict[str, BenchmarkScore], list[QuestionResult]]:
        """Run all configured models on all configured benchmarks.

        Returns:
            scores:      dict mapping "{role}/{benchmark}" → BenchmarkScore
            all_results: flat list of every QuestionResult for transcript saving
        """
        scores: dict[str, BenchmarkScore] = {}
        all_results: list[QuestionResult] = []

        for benchmark_spec in self.cfg.benchmarks:
            results_per_benchmark = self._run_benchmark(benchmark_spec)
            all_results.extend(results_per_benchmark)

            # Aggregate per (model, benchmark) pair
            for model_spec in self.cfg.models:
                model_results = [
                    r for r in results_per_benchmark if r.model_id == model_spec.model_id
                ]
                if model_results:
                    score = aggregate_scores(model_results)
                    score.provenance = self.result_provenance(
                        model_spec.model_id, benchmark_spec.name
                    )
                    key = f"{model_spec.role}/{benchmark_spec.name}"
                    scores[key] = score

        return scores, all_results

    def __init__(self, cfg: ExperimentConfig) -> None:
        super().__init__(cfg)
        self._benchmark_questions: dict[str, list] = {}
        self._benchmark_signatures: dict[str, str] = {}

    @property
    def reference_cache_score_version(self) -> str:
        return "phase1_v1"

    def load_models(self) -> None:
        """Load only models that are not fully satisfied by reference cache."""
        self._prepare_benchmarks()

        for spec in self.cfg.models:
            if self._can_use_cached_reference(spec):
                console.print(
                    f"Using cached reference results for [cyan]{spec.model_id}[/cyan] ({spec.role}); skipping model load."
                )
                continue

            console.print(f"Loading [cyan]{spec.model_id}[/cyan] ({spec.role}) …")
            self._pipelines[spec.model_id] = self._build_pipeline(spec)
        console.print()

    def _run_benchmark(self, spec: BenchmarkSpec) -> list[QuestionResult]:
        """Run all configured models on a single benchmark dataset."""
        console.rule(f"[cyan]{spec.name}[/cyan]")
        results: list[QuestionResult] = []

        questions = self._benchmark_questions[spec.name]
        console.print(f"  {len(questions)} questions loaded\n")

        for model_spec in self.cfg.models:
            model_results = self._evaluate_model(model_spec, spec.name, questions)
            results.extend(model_results)

        return results

    def _load_benchmark(self, spec: BenchmarkSpec) -> list:
        """Load questions from the specified benchmark.

        Returns a list of benchmark-specific items (TriviaQAItem, MMLUItem,
        or LogicPuzzle). The caller handles formatting via the appropriate
        format_prompt() function.
        """
        if spec.name == "triviaqa":
            return triviaqa.load_triviaqa(samples=spec.samples, seed=spec.seed)

        if spec.name == "mmlu":
            return mmlu.load_mmlu(
                subjects=spec.mmlu_subjects,
                samples=spec.samples,
                seed=spec.seed,
            )

        if spec.name == "synthetic":
            return synthetic.generate_puzzles(
                n=spec.samples or 500,
                seed=spec.seed,
                depth_range=self.cfg.synthetic.depth_range,
                puzzle_types=self.cfg.synthetic.puzzle_types,
            )

        raise ValueError(f"Unknown benchmark: {spec.name}")

    def _prepare_benchmarks(self) -> None:
        """Load benchmark inputs once and compute deterministic cache signatures."""
        if self._benchmark_questions:
            return

        for spec in self.cfg.benchmarks:
            questions = self._load_benchmark(spec)
            self._benchmark_questions[spec.name] = questions
            self._benchmark_signatures[spec.name] = self._compute_benchmark_signature(
                spec.name, questions
            )

    def _compute_benchmark_signature(self, benchmark_name: str, questions: list) -> str:
        payload: list[dict[str, str]] = []
        for item in questions:
            prompt, expected, question_id = self._format_item(benchmark_name, item)
            payload.append(
                {
                    "id": question_id,
                    "prompt": prompt,
                    "expected": json.dumps(expected, sort_keys=True),
                }
            )

        digest = hashlib.sha256(
            json.dumps(
                {
                    "score_version": self.reference_cache_score_version,
                    "benchmark": benchmark_name,
                    "questions": payload,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return digest[:16]

    def _can_use_cached_reference(self, model_spec: ModelSpec) -> bool:
        if model_spec.role != "large":
            return False
        if not self.cfg.logging.use_reference_cache or self.cfg.logging.refresh_reference_cache:
            return False

        return all(
            self._cache_path(model_spec, benchmark_spec.name).exists()
            for benchmark_spec in self.cfg.benchmarks
        )

    def _cache_path(self, model_spec: ModelSpec, benchmark_name: str) -> Path:
        signature = self._benchmark_signatures[benchmark_name]
        return self.reference_cache_path(model_spec.model_id, benchmark_name, signature)

    def _load_cached_results(
        self,
        model_spec: ModelSpec,
        benchmark_name: str,
    ) -> list[QuestionResult] | None:
        if model_spec.role != "large" or not self.cfg.logging.use_reference_cache:
            return None
        if self.cfg.logging.refresh_reference_cache:
            return None

        path = self._cache_path(model_spec, benchmark_name)
        if not path.exists():
            return None

        cached_results = load_reference_cache(
            path,
            score_version=self.reference_cache_score_version,
            benchmark_signature=self._benchmark_signatures[benchmark_name],
        )
        if cached_results is None:
            return None

        console.print(
            f"  [dim]cache hit[/dim] [cyan]{model_spec.model_id.split('/')[-1]}[/cyan] / {benchmark_name}"
        )
        self.set_result_provenance(model_spec.model_id, benchmark_name, "cached")
        cache_metadata = load_cache_metadata(path) or {}
        self.set_result_metadata(
            model_spec.model_id,
            benchmark_name,
            {
                "cached_at": cache_metadata.get("created_at"),
                "cache_path": str(path),
            },
        )
        return cached_results

    def _save_cached_results(
        self,
        model_spec: ModelSpec,
        benchmark_name: str,
        results: list[QuestionResult],
    ) -> None:
        if model_spec.role != "large" or not self.cfg.logging.use_reference_cache:
            return

        path = self._cache_path(model_spec, benchmark_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        save_reference_cache(
            path,
            experiment_name=self.cfg.name,
            score_version=self.reference_cache_score_version,
            model_id=model_spec.model_id,
            role=model_spec.role,
            benchmark=benchmark_name,
            benchmark_signature=self._benchmark_signatures[benchmark_name],
            results=results,
        )
        console.print(
            f"  [dim]cached reference[/dim] [cyan]{model_spec.model_id.split('/')[-1]}[/cyan] / {benchmark_name}"
        )

    def _evaluate_model(
        self,
        model_spec: ModelSpec,
        benchmark_name: str,
        questions: list,
    ) -> list[QuestionResult]:
        """Run one model on all questions from one benchmark.

        Formats each question into a prompt, calls the model, scores
        the answer, and records the result.
        """
        cached = self._load_cached_results(model_spec, benchmark_name)
        if cached is not None:
            return cached

        self.set_result_provenance(model_spec.model_id, benchmark_name, "live")
        self.set_result_metadata(model_spec.model_id, benchmark_name, {})

        results: list[QuestionResult] = []
        correct = 0

        with self.progress_bar(
            len(questions), f"{model_spec.model_id} / {benchmark_name}"
        ) as progress:
            task = progress.add_task(
                f"[cyan]{model_spec.model_id.split('/')[-1]}[/cyan] on {benchmark_name}",
                total=len(questions),
            )

            for item in questions:
                prompt, expected, question_id = self._format_item(benchmark_name, item)
                predicted = self.generate(model_spec.model_id, prompt)
                is_correct = self._score_answer(benchmark_name, predicted, expected, item)

                if is_correct:
                    correct += 1

                results.append(
                    QuestionResult(
                        question_id=question_id,
                        question=prompt,
                        expected=str(expected),
                        predicted=predicted,
                        correct=is_correct,
                        model_id=model_spec.model_id,
                        benchmark=benchmark_name,
                    )
                )
                progress.advance(task)

        acc = correct / len(questions) * 100 if questions else 0
        console.print(
            f"  [bold]{model_spec.model_id.split('/')[-1]}[/bold] → "
            f"[green]{acc:.1f}%[/green] ({correct}/{len(questions)})\n"
        )
        self._save_cached_results(model_spec, benchmark_name, results)
        return results

    def _format_item(self, benchmark_name: str, item) -> tuple[str, object, str]:
        """Return (prompt, expected_answer, question_id) for any benchmark item."""
        if benchmark_name == "triviaqa":
            return triviaqa.format_prompt(item), item.answers, item.question_id
        if benchmark_name == "mmlu":
            return mmlu.format_prompt(item), item.answer, item.question_id
        if benchmark_name == "synthetic":
            return synthetic.format_prompt(item), item.answer, item.question_id
        raise ValueError(f"Unknown benchmark: {benchmark_name}")

    def _score_answer(self, benchmark_name: str, predicted: str, expected, item) -> bool:
        """Route scoring to the appropriate function for each benchmark."""
        if benchmark_name == "triviaqa":
            return score_triviaqa(predicted, expected)
        if benchmark_name == "mmlu":
            return score_mmlu(predicted, expected)
        if benchmark_name == "synthetic":
            return score_logic_puzzle(predicted, expected)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────


def build_default_config() -> ExperimentConfig:
    """Load the canonical Phase 1 experiment preset."""
    return ExperimentConfig.from_yaml(Path("configs/benchmarks/exp_01.yaml"))


def main() -> None:
    runner = BaselineRunner(build_default_config())
    runner.execute()


if __name__ == "__main__":
    main()
