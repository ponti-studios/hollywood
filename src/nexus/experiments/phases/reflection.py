"""
exp_03_reflection.py — Phase 3: Draft → Critique → Refine loop.

This phase reuses the existing benchmark tasks but measures whether an
explicit self-critique pass improves correctness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from rich.console import Console

from nexus.experiments.benchmark_support import format_item, load_benchmark, score_answer
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
    compute_correction_delta,
)

console = Console()


class ReflectionRunner(BaseRunner):
    def __init__(self, cfg: ExperimentConfig) -> None:
        super().__init__(cfg)
        self._benchmark_questions: dict[str, list[Any]] = {}
        self._benchmark_signatures: dict[str, str] = {}
        self._correction_deltas: dict[tuple[str, str], float] = {}

    @property
    def reference_cache_score_version(self) -> str:
        return "phase3_v1"

    def load_models(self) -> None:
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

    def run(self) -> tuple[dict[str, BenchmarkScore], list[QuestionResult]]:
        scores: dict[str, BenchmarkScore] = {}
        all_results: list[QuestionResult] = []

        for benchmark_spec in self.cfg.benchmarks:
            results_per_benchmark = self._run_benchmark(benchmark_spec)
            all_results.extend(results_per_benchmark)

            for model_spec in self.cfg.models:
                model_results = [
                    r for r in results_per_benchmark if r.model_id == model_spec.model_id
                ]
                if not model_results:
                    continue
                score = aggregate_scores(model_results)
                score.correction_delta = self._correction_deltas.get(
                    (model_spec.model_id, benchmark_spec.name)
                )
                score.provenance = self.result_provenance(model_spec.model_id, benchmark_spec.name)
                scores[f"{model_spec.role}/{benchmark_spec.name}"] = score

        return scores, all_results

    def _run_benchmark(self, spec: BenchmarkSpec) -> list[QuestionResult]:
        console.rule(f"[cyan]{spec.name}[/cyan]")
        questions = self._benchmark_questions[spec.name]
        console.print(f"  {len(questions)} questions loaded\n")

        results: list[QuestionResult] = []
        for model_spec in self.cfg.models:
            model_results, delta = self._evaluate_model(model_spec, spec.name, questions)
            self._correction_deltas[(model_spec.model_id, spec.name)] = delta
            results.extend(model_results)
        return results

    def _prepare_benchmarks(self) -> None:
        if self._benchmark_questions:
            return
        for spec in self.cfg.benchmarks:
            questions = load_benchmark(spec, self.cfg)
            self._benchmark_questions[spec.name] = questions
            self._benchmark_signatures[spec.name] = self._compute_benchmark_signature(
                spec.name, questions
            )

    def _compute_benchmark_signature(self, benchmark_name: str, questions: list[Any]) -> str:
        payload: list[dict[str, str]] = []
        for item in questions:
            prompt, expected, question_id = format_item(benchmark_name, item)
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

    def _cache_path(self, model_spec: ModelSpec, benchmark_name: str) -> Path:
        return self.reference_cache_path(
            model_spec.model_id,
            benchmark_name,
            self._benchmark_signatures[benchmark_name],
        )

    def _can_use_cached_reference(self, model_spec: ModelSpec) -> bool:
        if model_spec.role != "large":
            return False
        if not self.cfg.logging.use_reference_cache or self.cfg.logging.refresh_reference_cache:
            return False
        return all(self._cache_path(model_spec, spec.name).exists() for spec in self.cfg.benchmarks)

    def _load_cached_results(
        self, model_spec: ModelSpec, benchmark_name: str
    ) -> tuple[list[QuestionResult], float] | None:
        if model_spec.role != "large" or not self.cfg.logging.use_reference_cache:
            return None
        if self.cfg.logging.refresh_reference_cache:
            return None

        path = self._cache_path(model_spec, benchmark_name)
        cached_results = load_reference_cache(
            path,
            score_version=self.reference_cache_score_version,
            benchmark_signature=self._benchmark_signatures[benchmark_name],
        )
        if cached_results is None:
            return None

        metadata = load_cache_metadata(path) or {}
        delta = float(metadata.get("correction_delta", 0.0))
        self.set_result_provenance(model_spec.model_id, benchmark_name, "cached")
        self.set_result_metadata(
            model_spec.model_id,
            benchmark_name,
            {"cached_at": metadata.get("created_at"), "cache_path": str(path)},
        )
        console.print(
            f"  [dim]cache hit[/dim] [cyan]{model_spec.model_id.split('/')[-1]}[/cyan] / {benchmark_name}"
        )
        return cached_results, delta

    def _save_cached_results(
        self,
        model_spec: ModelSpec,
        benchmark_name: str,
        results: list[QuestionResult],
        correction_delta: float,
    ) -> None:
        if model_spec.role != "large" or not self.cfg.logging.use_reference_cache:
            return
        path = self._cache_path(model_spec, benchmark_name)
        save_reference_cache(
            path,
            experiment_name=self.cfg.name,
            score_version=self.reference_cache_score_version,
            model_id=model_spec.model_id,
            role=model_spec.role,
            benchmark=benchmark_name,
            benchmark_signature=self._benchmark_signatures[benchmark_name],
            results=results,
            extra_metadata={"correction_delta": correction_delta},
        )
        console.print(
            f"  [dim]cached reference[/dim] [cyan]{model_spec.model_id.split('/')[-1]}[/cyan] / {benchmark_name}"
        )

    def _evaluate_model(
        self,
        model_spec: ModelSpec,
        benchmark_name: str,
        questions: list[Any],
    ) -> tuple[list[QuestionResult], float]:
        cached = self._load_cached_results(model_spec, benchmark_name)
        if cached is not None:
            return cached

        self.set_result_provenance(model_spec.model_id, benchmark_name, "live")
        self.set_result_metadata(model_spec.model_id, benchmark_name, {})

        results: list[QuestionResult] = []
        draft_results: list[QuestionResult] = []
        correct = 0

        with self.progress_bar(
            len(questions), f"{model_spec.model_id} / {benchmark_name}"
        ) as progress:
            task = progress.add_task(
                f"[cyan]{model_spec.model_id.split('/')[-1]}[/cyan] on {benchmark_name}",
                total=len(questions),
            )
            for item in questions:
                question_prompt, expected, question_id = format_item(benchmark_name, item)
                draft = self.generate(
                    model_spec.model_id, self._draft_prompt(question_prompt)
                ).strip()
                critique = self.generate(
                    model_spec.model_id,
                    self._critique_prompt(question_prompt, draft),
                ).strip()
                refined = self.generate(
                    model_spec.model_id,
                    self._refine_prompt(question_prompt, draft, critique),
                ).strip()

                draft_correct = score_answer(benchmark_name, draft, expected, item)
                refined_correct = score_answer(benchmark_name, refined, expected, item)
                if refined_correct:
                    correct += 1

                draft_results.append(
                    QuestionResult(
                        question_id=question_id,
                        question=question_prompt,
                        expected=str(expected),
                        predicted=draft,
                        correct=draft_correct,
                        model_id=model_spec.model_id,
                        benchmark=benchmark_name,
                    )
                )
                results.append(
                    QuestionResult(
                        question_id=question_id,
                        question=question_prompt,
                        expected=str(expected),
                        predicted=refined,
                        correct=refined_correct,
                        model_id=model_spec.model_id,
                        benchmark=benchmark_name,
                        draft=draft,
                        critique=critique,
                    )
                )
                progress.advance(task)

        correction_delta = compute_correction_delta(draft_results, results)
        acc = correct / len(questions) * 100 if questions else 0.0
        console.print(
            f"  [bold]{model_spec.model_id.split('/')[-1]}[/bold] → [green]{acc:.1f}%[/green] ({correct}/{len(questions)})"
            f"  Δ {correction_delta:+.1f}pp\n"
        )
        self._save_cached_results(model_spec, benchmark_name, results, correction_delta)
        return results, correction_delta

    def _draft_prompt(self, task_prompt: str) -> str:
        return f"Solve the following task. Give your best first answer.\n\n{task_prompt}"

    def _critique_prompt(self, task_prompt: str, draft: str) -> str:
        return (
            "Review the proposed answer. Do not re-solve from scratch unless necessary. "
            "Find likely flaws, wrong assumptions, missing steps, or reasons the answer may be incorrect. "
            "If it looks correct, say NO ISSUES FOUND.\n\n"
            f"Task:\n{task_prompt}\n\n"
            f"Proposed answer:\n{draft}\n"
        )

    def _refine_prompt(self, task_prompt: str, draft: str, critique: str) -> str:
        return (
            "You wrote an initial answer and then critiqued it. "
            "Write an improved final answer that fixes the critique where appropriate. "
            "Return only the final answer.\n\n"
            f"Task:\n{task_prompt}\n\n"
            f"Initial answer:\n{draft}\n\n"
            f"Critique:\n{critique}\n"
        )


def build_default_config() -> ExperimentConfig:
    """Load the canonical Phase 3 experiment preset."""
    return ExperimentConfig.from_yaml(Path("configs/benchmarks/exp_03.yaml"))


def main() -> None:
    ReflectionRunner(build_default_config()).execute()


if __name__ == "__main__":
    main()
