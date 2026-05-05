from __future__ import annotations

import asyncio
from pathlib import Path

from nexus.api.routers.experiments import _execute, _experiment_from_config
from nexus.evaluation import EvaluationStore
from nexus.experiments import ExperimentStore
from nexus.experiments.config import (
    BenchmarkSpec,
    ExperimentConfig,
    LoggingSpec,
    ModelSpec,
    SyntheticPuzzleSpec,
)
from nexus.experiments.schema import ExperimentSchema, ExperimentVariantSchema


class _FakeScore:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


def _build_config(tmp_path: Path) -> ExperimentConfig:
    return ExperimentConfig(
        name="exp_test",
        description="Test experiment",
        phase=1,
        models=[ModelSpec(model_id="google/gemma-4-e2b", role="small")],
        benchmarks=[BenchmarkSpec(name="triviaqa", samples=10)],
        synthetic=SyntheticPuzzleSpec(),
        logging=LoggingSpec(wandb_project=None, output_dir=str(tmp_path / "results")),
    )


def test_experiment_store_saves_and_loads_schema(tmp_path: Path) -> None:
    store = ExperimentStore(tmp_path / "experiments.db")
    record = ExperimentSchema(
        id="exp_123",
        name="compare-variants",
        hypothesis="A beats B",
        capability="text",
        status="pending",
        benchmark_ids=["triviaqa"],
        variant_specs=[ExperimentVariantSchema(id="small-1", model_id="google/gemma-4-e2b")],
        run_ids=[],
        evaluation_ids=[],
        config={"phase": 1},
        summary={"phase": 1},
        winner=None,
        error=None,
        created_at=1.0,
        started_at=1.0,
        completed_at=None,
    )

    store.save(record)

    loaded = store.get("exp_123")
    assert loaded is not None
    assert loaded.id == "exp_123"
    assert loaded.name == "compare-variants"
    assert loaded.variant_specs[0].id == "small-1"
    assert loaded.config == {"phase": 1}
    assert loaded.summary == {"phase": 1}


def test_execute_marks_experiment_completed_and_persists_scores(
    tmp_path: Path, monkeypatch
) -> None:
    store = ExperimentStore(tmp_path / "experiments.db")
    cfg = _build_config(tmp_path)
    experiment = _experiment_from_config(cfg, "exp_complete")
    store.save(experiment)

    class _Runner:
        def execute(self) -> dict[str, _FakeScore]:
            return {"triviaqa": _FakeScore({"accuracy": 0.9})}

    monkeypatch.setattr("nexus.api.routers.experiments._runner_for", lambda cfg: _Runner())

    evaluation_store = EvaluationStore(tmp_path / "experiments.db")

    asyncio.run(_execute("exp_complete", cfg, store, evaluation_store))

    loaded = store.get("exp_complete")
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.completed_at is not None
    assert loaded.summary is not None
    assert loaded.summary["phase"] == 1
    assert loaded.summary["scores"] == {"triviaqa": {"accuracy": 0.9}}
    assert loaded.summary["output_dir"].endswith("results/exp_test")
    assert len(loaded.evaluation_ids) == 1

    evaluation = evaluation_store.get(loaded.evaluation_ids[0])
    assert evaluation is not None
    assert evaluation.subject_type == "experiment"
    assert evaluation.subject_id == "exp_complete"
    assert evaluation.benchmark_id == "triviaqa"
    assert evaluation.metrics == {"accuracy": 0.9}


def test_execute_marks_experiment_failed_and_persists_error(tmp_path: Path, monkeypatch) -> None:
    store = ExperimentStore(tmp_path / "experiments.db")
    cfg = _build_config(tmp_path)
    experiment = _experiment_from_config(cfg, "exp_failed")
    store.save(experiment)

    class _Runner:
        def execute(self) -> dict:
            raise RuntimeError("boom")

    monkeypatch.setattr("nexus.api.routers.experiments._runner_for", lambda cfg: _Runner())

    evaluation_store = EvaluationStore(tmp_path / "experiments.db")

    asyncio.run(_execute("exp_failed", cfg, store, evaluation_store))

    loaded = store.get("exp_failed")
    assert loaded is not None
    assert loaded.status == "failed"
    assert loaded.completed_at is not None
    assert loaded.error is not None
    assert "RuntimeError: boom" in loaded.error["traceback"]
    assert loaded.evaluation_ids == []
    assert evaluation_store.list(subject_type="experiment", subject_id="exp_failed") == []
