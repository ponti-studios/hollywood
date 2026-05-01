from __future__ import annotations

from types import SimpleNamespace

from experiments.exp_02_open_book import OpenBookRunner
from experiments.exp_03_reflection import ReflectionRunner
from nexus.experiments.config import BenchmarkSpec, ExperimentConfig, LoggingSpec, ModelSpec


def test_open_book_runner_uses_search_and_records_tool_calls(monkeypatch, tmp_path) -> None:
    cfg = ExperimentConfig(
        name="exp_02_open_book",
        description="test",
        phase=2,
        models=[ModelSpec(model_id="small-model", role="small")],
        benchmarks=[BenchmarkSpec(name="triviaqa", samples=1)],
        logging=LoggingSpec(wandb_project=None, output_dir=str(tmp_path / "results")),
    )
    runner = OpenBookRunner(cfg)

    items = [SimpleNamespace(question_id="q1")]
    monkeypatch.setattr("experiments.exp_02_open_book.load_benchmark", lambda spec, cfg: items)
    monkeypatch.setattr(
        "experiments.exp_02_open_book.format_item",
        lambda benchmark_name, item: ("Question: capital of France", ["Paris"], item.question_id),
    )
    monkeypatch.setattr(
        "experiments.exp_02_open_book.score_answer",
        lambda benchmark_name, predicted, expected, item: predicted == "Paris",
    )

    class FakeTool:
        def search(self, query: str, limit: int = 3) -> str:
            assert query == "capital of france"
            return "Source: Paris\nSnippet: Paris is the capital of France."

    runner._tool = FakeTool()
    runner._prepare_benchmarks()

    responses = iter(["[SEARCH: capital of france]", "[ANSWER: Paris]"])
    monkeypatch.setattr(runner, "generate", lambda model_id, prompt: next(responses))

    results = runner._evaluate_model(cfg.models[0], "triviaqa", runner._benchmark_questions["triviaqa"])

    assert len(results) == 1
    assert results[0].predicted == "Paris"
    assert results[0].tool_calls == 1
    assert results[0].correct is True


def test_reflection_runner_computes_correction_delta(monkeypatch, tmp_path) -> None:
    cfg = ExperimentConfig(
        name="exp_03_reflection",
        description="test",
        phase=3,
        models=[ModelSpec(model_id="small-model", role="small")],
        benchmarks=[BenchmarkSpec(name="synthetic", samples=1)],
        logging=LoggingSpec(wandb_project=None, output_dir=str(tmp_path / "results")),
    )
    runner = ReflectionRunner(cfg)

    items = [SimpleNamespace(question_id="q1")]
    monkeypatch.setattr("experiments.exp_03_reflection.load_benchmark", lambda spec, cfg: items)
    monkeypatch.setattr(
        "experiments.exp_03_reflection.format_item",
        lambda benchmark_name, item: ("Question: Is Tixby a Wumble?", "Yes", item.question_id),
    )
    monkeypatch.setattr(
        "experiments.exp_03_reflection.score_answer",
        lambda benchmark_name, predicted, expected, item: predicted.strip() == expected,
    )
    runner._prepare_benchmarks()

    responses = iter(["No", "The answer contradicts the premises.", "Yes"])
    monkeypatch.setattr(runner, "generate", lambda model_id, prompt: next(responses))

    results, delta = runner._evaluate_model(cfg.models[0], "synthetic", runner._benchmark_questions["synthetic"])

    assert delta == 100.0
    assert len(results) == 1
    assert results[0].draft == "No"
    assert results[0].critique == "The answer contradicts the premises."
    assert results[0].predicted == "Yes"
    assert results[0].correct is True