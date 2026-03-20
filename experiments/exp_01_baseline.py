"""
exp_01_baseline.py — Phase 1: The "Category Error" Baseline

What this experiment proves
────────────────────────────
Large models (70B+) are trained on vastly more data, giving them a much
richer store of memorized facts. But do their extra parameters also make
them better *reasoners*, or do they just know more trivia?

This experiment separates the two by running both a small model (3B/4B)
and a large reference model on:

  1. TriviaQA  — knowledge-heavy, tests memorized facts
  2. MMLU      — knowledge-heavy, tests academic subject knowledge
  3. Synthetic — pure logic, tests reasoning with made-up words

Expected outcome:
  - Large model wins big on TriviaQA and MMLU  (it has more facts stored)
  - Small model performs *surprisingly close* on Synthetic  (it can reason too)
  - The gap on Synthetic is the key finding — it means the 3B model's
    reasoning is nearly as capable, just its fact-store is smaller

If the gap on Synthetic is also large, we need to revisit the hypothesis.

Usage:
    # Full run with both models (slow):
    python experiments/exp_01_baseline.py

    # Quick test with 50 samples per benchmark (fast):
    python experiments/exp_01_baseline.py --samples 50 --no-large-model

    # Custom config:
    python experiments/exp_01_baseline.py --config experiments/configs/exp_01.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the package is importable when running the script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console

from nexus.experiments.config import ExperimentConfig, ModelSpec, BenchmarkSpec
from nexus.experiments.runner import BaseRunner
from nexus.experiments.scoring import (
    BenchmarkScore,
    QuestionResult,
    aggregate_scores,
    score_triviaqa,
    score_mmlu,
    score_logic_puzzle,
)
from nexus.experiments.benchmarks import triviaqa, mmlu, synthetic

console = Console()


class BaselineRunner(BaseRunner):
    """Phase 1 runner — evaluates models on all three benchmark types.

    Runs each model on each benchmark sequentially and collects results.
    No tools, no reflection — this is the pure "closed book" baseline
    that every subsequent phase will be compared against.
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
                model_results = [r for r in results_per_benchmark if r.model_id == model_spec.model_id]
                if model_results:
                    score = aggregate_scores(model_results)
                    key = f"{model_spec.role}/{benchmark_spec.name}"
                    scores[key] = score

        return scores, all_results

    def _run_benchmark(self, spec: BenchmarkSpec) -> list[QuestionResult]:
        """Run all configured models on a single benchmark dataset."""
        console.rule(f"[cyan]{spec.name}[/cyan]")
        results: list[QuestionResult] = []

        questions = self._load_benchmark(spec)
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
        results: list[QuestionResult] = []
        correct = 0

        with self.progress_bar(len(questions), f"{model_spec.model_id} / {benchmark_name}") as progress:
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

def build_default_config(
    small_model: str,
    large_model: str | None,
    samples: int,
    no_wandb: bool,
) -> ExperimentConfig:
    """Build an ExperimentConfig programmatically when no YAML is provided.

    This lets you run quick experiments without writing a config file:
        python experiments/exp_01_baseline.py --samples 50
    """
    from nexus.experiments.config import LoggingSpec, SyntheticPuzzleSpec

    models = [
        ModelSpec(model_id=small_model, role="small"),
    ]
    if large_model:
        models.append(ModelSpec(model_id=large_model, role="large"))

    benchmarks = [
        BenchmarkSpec(name="triviaqa", samples=samples),
        BenchmarkSpec(name="mmlu", samples=samples),
        BenchmarkSpec(name="synthetic", samples=samples),
    ]

    return ExperimentConfig(
        name="exp_01_baseline",
        description="Phase 1: Closed-book baseline — 3B vs 70B on knowledge vs logic",
        phase=1,
        models=models,
        benchmarks=benchmarks,
        synthetic=SyntheticPuzzleSpec(),
        logging=LoggingSpec(wandb_project=None if no_wandb else "3b-logic-broker"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1: Closed-book baseline experiment"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to experiment YAML config. If omitted, uses CLI flags.",
    )
    parser.add_argument(
        "--small-model",
        default="google/gemma-3-4b-it",
        help="Small model to evaluate (default: google/gemma-3-4b-it)",
    )
    parser.add_argument(
        "--large-model",
        default=None,
        help="Large reference model (optional, e.g. meta-llama/Meta-Llama-3-70B-Instruct)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=500,
        help="Questions per benchmark (default: 500). Use 50 for a quick sanity check.",
    )
    parser.add_argument(
        "--no-wandb",
        action="store_true",
        help="Disable Weights & Biases logging (useful for offline/dev runs)",
    )
    args = parser.parse_args()

    if args.config:
        cfg = ExperimentConfig.from_yaml(args.config)
    else:
        cfg = build_default_config(
            small_model=args.small_model,
            large_model=args.large_model,
            samples=args.samples,
            no_wandb=args.no_wandb,
        )

    runner = BaselineRunner(cfg)
    runner.execute()


if __name__ == "__main__":
    main()
