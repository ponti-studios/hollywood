from __future__ import annotations

import time
from pathlib import Path

import click
import pytest
from rich.console import Console

from nexus.cli.experiment import inspect_reference_cache, list_reference_caches
from nexus.experiments.config import ExperimentConfig, LoggingSpec
from nexus.experiments.reference_cache import (
    find_reference_caches,
    save_reference_cache,
    summarize_cache_file,
)
from nexus.experiments.runner import BaseRunner
from nexus.experiments.scoring import BenchmarkScore, QuestionResult


class DummyRunner(BaseRunner):
    def run(self):
        return {}, []


def test_reference_cache_listing_and_summary(tmp_path: Path) -> None:
    cache_path = (
        tmp_path / "cache" / "exp_01_baseline" / "meta-llama__model" / "triviaqa_abc123.json"
    )
    save_reference_cache(
        cache_path,
        experiment_name="exp_01_baseline",
        score_version="phase1_v1",
        model_id="meta-llama/model",
        role="large",
        benchmark="triviaqa",
        benchmark_signature="abc123",
        results=[
            QuestionResult(
                question_id="q1",
                question="Prompt 1",
                expected="Paris",
                predicted="Paris",
                correct=True,
                model_id="meta-llama/model",
                benchmark="triviaqa",
            ),
            QuestionResult(
                question_id="q2",
                question="Prompt 2",
                expected="Rome",
                predicted="Milan",
                correct=False,
                model_id="meta-llama/model",
                benchmark="triviaqa",
            ),
        ],
    )

    matches = find_reference_caches(
        tmp_path / "cache", experiment="exp_01_baseline", benchmark="triviaqa"
    )
    assert matches == [cache_path]

    summary = summarize_cache_file(cache_path)
    assert summary["experiment"] == "exp_01_baseline"
    assert summary["model_id"] == "meta-llama/model"
    assert summary["benchmark"] == "triviaqa"
    assert summary["correct"] == 1
    assert summary["total"] == 2
    assert summary["accuracy"] == 0.5


def test_comparison_table_shows_provenance(monkeypatch) -> None:
    runner = DummyRunner(
        ExperimentConfig(
            name="exp_01_baseline",
            description="test",
            logging=LoggingSpec(wandb_project=None),
        )
    )
    capture_console = Console(record=True, width=120)
    import nexus.experiments.runner as runner_module

    monkeypatch.setattr(runner_module, "console", capture_console)

    runner.print_comparison_table(
        {
            "small/triviaqa": BenchmarkScore(
                model_id="small-model",
                benchmark="triviaqa",
                accuracy=0.5,
                correct_count=25,
                total=50,
                provenance="live",
            ),
            "large/triviaqa": BenchmarkScore(
                model_id="large-model",
                benchmark="triviaqa",
                accuracy=0.8,
                correct_count=40,
                total=50,
                provenance="cached",
            ),
        }
    )

    rendered = capture_console.export_text()
    assert "Small Src" in rendered
    assert "Large Src" in rendered
    assert "live" in rendered
    assert "cached" in rendered
    assert "+30.0pp" in rendered


def test_comparison_table_warns_on_stale_cache(monkeypatch) -> None:
    runner = DummyRunner(
        ExperimentConfig(
            name="exp_01_baseline",
            description="test",
            logging=LoggingSpec(wandb_project=None, reference_cache_warn_after_hours=1),
        )
    )
    capture_console = Console(record=True, width=140)
    import nexus.experiments.runner as runner_module

    monkeypatch.setattr(runner_module, "console", capture_console)
    runner.set_result_metadata(
        "large-model",
        "triviaqa",
        {
            "cached_at": int(time.time() - 3 * 3600),
            "cache_path": ".data/benchmarks/cache/exp_01_baseline/large-model/triviaqa.json",
        },
    )

    runner.print_comparison_table(
        {
            "small/triviaqa": BenchmarkScore(
                model_id="small-model",
                benchmark="triviaqa",
                accuracy=0.5,
                correct_count=25,
                total=50,
                provenance="live",
            ),
            "large/triviaqa": BenchmarkScore(
                model_id="large-model",
                benchmark="triviaqa",
                accuracy=0.8,
                correct_count=40,
                total=50,
                provenance="cached",
            ),
        }
    )

    rendered = capture_console.export_text()
    assert "cached!" in rendered
    assert "Warning:" in rendered

def test_cache_cli_json_output(monkeypatch, tmp_path: Path) -> None:
    cache_path = (
        tmp_path
        / "cache"
        / "exp_01_baseline"
        / "Qwen__Qwen2.5-7B-Instruct"
        / "triviaqa_abc123.json"
    )
    save_reference_cache(
        cache_path,
        experiment_name="exp_01_baseline",
        score_version="phase1_v1",
        model_id="Qwen/Qwen3.5-4B",
        role="large",
        benchmark="triviaqa",
        benchmark_signature="abc123",
        results=[
            QuestionResult(
                question_id="q1",
                question="Prompt 1",
                expected="Paris",
                predicted="Paris",
                correct=True,
                model_id="Qwen/Qwen3.5-4B",
                benchmark="triviaqa",
            )
        ],
    )

    capture_console = Console(record=True, width=140)
    import nexus.cli.experiment as experiment_module

    monkeypatch.setattr(experiment_module, "console", capture_console)

    with pytest.raises(click.exceptions.Exit):
        list_reference_caches(
            cache_dir=tmp_path / "cache",
            experiment=None,
            model=None,
            benchmark=None,
            as_json=True,
        )

    rendered = capture_console.export_text()
    assert '"model_id": "Qwen/Qwen3.5-4B"' in rendered

    capture_console = Console(record=True, width=140)
    monkeypatch.setattr(experiment_module, "console", capture_console)
    with pytest.raises(click.exceptions.Exit):
        inspect_reference_cache(cache_path=cache_path, as_json=True)

    rendered = capture_console.export_text()
    assert '"results_total": 1' in rendered
