from __future__ import annotations

from typing import Any

from nexus.experiments.benchmarks import mmlu, synthetic, triviaqa
from nexus.experiments.config import BenchmarkSpec, ExperimentConfig
from nexus.experiments.scoring import score_logic_puzzle, score_mmlu, score_triviaqa


def load_benchmark(spec: BenchmarkSpec, cfg: ExperimentConfig) -> list[Any]:
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
            depth_range=cfg.synthetic.depth_range,
            puzzle_types=cfg.synthetic.puzzle_types,
        )

    raise ValueError(f"Unknown benchmark: {spec.name}")


def format_item(benchmark_name: str, item: Any) -> tuple[str, object, str]:
    if benchmark_name == "triviaqa":
        return triviaqa.format_prompt(item), item.answers, item.question_id
    if benchmark_name == "mmlu":
        return mmlu.format_prompt(item), item.answer, item.question_id
    if benchmark_name == "synthetic":
        return synthetic.format_prompt(item), item.answer, item.question_id
    raise ValueError(f"Unknown benchmark: {benchmark_name}")


def score_answer(benchmark_name: str, predicted: str, expected: object, item: Any) -> bool:
    if benchmark_name == "triviaqa":
        return score_triviaqa(predicted, expected)
    if benchmark_name == "mmlu":
        return score_mmlu(predicted, expected)
    if benchmark_name == "synthetic":
        return score_logic_puzzle(predicted, expected)
    return False