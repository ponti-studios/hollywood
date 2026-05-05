from __future__ import annotations

from pathlib import Path

from nexus.evaluation import EvaluationStore
from nexus.evaluation.schema import EvaluationSchema


def test_evaluation_store_saves_and_loads_schema(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path / "evaluations.db")
    record = EvaluationSchema(
        id="eval_123",
        subject_type="experiment",
        subject_id="exp_123",
        capability="text",
        benchmark_id="triviaqa",
        scorer="benchmark_score",
        rubric="phase-1-benchmark-score",
        metrics={"accuracy": 0.9},
        judgment="90.0%",
        notes="Stored from experiment exp_123",
        created_at=1.0,
    )

    store.save(record)

    loaded = store.get("eval_123")
    assert loaded is not None
    assert loaded.id == "eval_123"
    assert loaded.subject_type == "experiment"
    assert loaded.metrics == {"accuracy": 0.9}


def test_evaluation_store_lists_by_subject_and_benchmark(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path / "evaluations.db")
    records = [
        EvaluationSchema(
            id="eval_a",
            subject_type="experiment",
            subject_id="exp_1",
            capability="text",
            benchmark_id="triviaqa",
            scorer="benchmark_score",
            metrics={"accuracy": 0.5},
            created_at=1.0,
        ),
        EvaluationSchema(
            id="eval_b",
            subject_type="experiment",
            subject_id="exp_1",
            capability="text",
            benchmark_id="mmlu",
            scorer="benchmark_score",
            metrics={"accuracy": 0.6},
            created_at=2.0,
        ),
        EvaluationSchema(
            id="eval_c",
            subject_type="run",
            subject_id="run_1",
            capability="audio",
            benchmark_id="audio_nat",
            scorer="judge:gpt-4.1",
            metrics={"naturalness": 4.4},
            created_at=3.0,
        ),
    ]

    for record in records:
        store.save(record)

    exp_records = store.list(subject_type="experiment", subject_id="exp_1")
    assert [record.id for record in exp_records] == ["eval_b", "eval_a"]

    benchmark_records = store.list(benchmark_id="triviaqa")
    assert [record.id for record in benchmark_records] == ["eval_a"]
