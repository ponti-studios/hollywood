from __future__ import annotations

from types import SimpleNamespace

from experiments.exp_01_baseline import BaselineRunner
from nexus.experiments.config import BenchmarkSpec, ExperimentConfig, LoggingSpec, ModelSpec, SyntheticPuzzleSpec
from nexus.experiments.scoring import QuestionResult


def build_config(tmp_path, benchmarks: list[BenchmarkSpec]) -> ExperimentConfig:
    return ExperimentConfig(
        name="exp_01_baseline",
        description="cache test",
        phase=1,
        models=[
            ModelSpec(model_id="small-model", role="small"),
            ModelSpec(model_id="large-model", role="large"),
        ],
        benchmarks=benchmarks,
        synthetic=SyntheticPuzzleSpec(),
        logging=LoggingSpec(
            wandb_project=None,
            output_dir=str(tmp_path / "results"),
            reference_cache_dir=str(tmp_path / "cache"),
        ),
    )


def install_fake_benchmarks(runner: BaselineRunner, benchmark_items: dict[str, list[SimpleNamespace]]) -> None:
    def fake_load(spec: BenchmarkSpec) -> list[SimpleNamespace]:
        return benchmark_items[spec.name]

    def fake_format(benchmark_name: str, item: SimpleNamespace) -> tuple[str, str, str]:
        return item.prompt, item.expected, item.question_id

    runner._load_benchmark = fake_load  # type: ignore[method-assign]
    runner._format_item = fake_format  # type: ignore[method-assign]


def test_large_model_uses_cached_results(tmp_path) -> None:
    cfg = build_config(tmp_path, [BenchmarkSpec(name="synthetic", samples=2)])
    runner = BaselineRunner(cfg)
    benchmark_items = {
        "synthetic": [
            SimpleNamespace(question_id="q1", prompt="Prompt 1", expected="Yes"),
            SimpleNamespace(question_id="q2", prompt="Prompt 2", expected="No"),
        ]
    }
    install_fake_benchmarks(runner, benchmark_items)
    runner._prepare_benchmarks()

    cached_results = [
        QuestionResult(
            question_id="q1",
            question="Prompt 1",
            expected="Yes",
            predicted="Yes",
            correct=True,
            model_id="large-model",
            benchmark="synthetic",
        ),
        QuestionResult(
            question_id="q2",
            question="Prompt 2",
            expected="No",
            predicted="No",
            correct=True,
            model_id="large-model",
            benchmark="synthetic",
        ),
    ]
    runner._save_cached_results(cfg.models[1], "synthetic", cached_results)

    def fail_generate(model_id: str, prompt: str) -> str:
        raise AssertionError("generate() should not be called on a cache hit")

    runner.generate = fail_generate  # type: ignore[method-assign]

    results = runner._evaluate_model(
        cfg.models[1],
        "synthetic",
        runner._benchmark_questions["synthetic"],
    )

    assert [result.predicted for result in results] == ["Yes", "No"]
    assert all(result.model_id == "large-model" for result in results)


def test_load_models_skips_large_reference_when_cache_is_complete(tmp_path) -> None:
    cfg = build_config(
        tmp_path,
        [
            BenchmarkSpec(name="triviaqa", samples=1),
            BenchmarkSpec(name="mmlu", samples=1),
        ],
    )
    runner = BaselineRunner(cfg)
    benchmark_items = {
        "triviaqa": [SimpleNamespace(question_id="t1", prompt="Trivia prompt", expected="Paris")],
        "mmlu": [SimpleNamespace(question_id="m1", prompt="MMLU prompt", expected="A")],
    }
    install_fake_benchmarks(runner, benchmark_items)
    runner._prepare_benchmarks()

    for benchmark_name, items in benchmark_items.items():
        runner._save_cached_results(
            cfg.models[1],
            benchmark_name,
            [
                QuestionResult(
                    question_id=items[0].question_id,
                    question=items[0].prompt,
                    expected=items[0].expected,
                    predicted=items[0].expected,
                    correct=True,
                    model_id="large-model",
                    benchmark=benchmark_name,
                )
            ],
        )

    loaded_models: list[str] = []

    def fake_build_pipeline(spec: ModelSpec) -> object:
        loaded_models.append(spec.model_id)
        return object()

    runner._build_pipeline = fake_build_pipeline  # type: ignore[method-assign]

    runner.load_models()

    assert loaded_models == ["small-model"]
    assert "small-model" in runner._pipelines
    assert "large-model" not in runner._pipelines