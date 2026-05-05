from __future__ import annotations

from pathlib import Path

from nexus.api.store import InferenceRecord, InferenceStore
from nexus.runs import RunRecord, RunStore


def test_run_store_saves_and_loads_platform_run(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.db")
    record = RunRecord.inference(
        id="run-1",
        model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
        messages=[{"role": "user", "content": "hello"}],
        response="world",
        prompt_tokens=4,
        completion_tokens=2,
        latency_ms=12.5,
        created_at=123.0,
    )

    store.save(record)

    loaded = store.get("run-1")
    assert loaded is not None
    assert loaded.id == "run-1"
    assert loaded.kind == "inference"
    assert loaded.capability == "text"
    assert loaded.status == "completed"
    assert loaded.model_id == "HuggingFaceTB/SmolLM2-135M-Instruct"
    assert loaded.input == {"messages": [{"role": "user", "content": "hello"}]}
    assert loaded.output == {"response": "world"}
    assert loaded.metrics == {
        "prompt_tokens": 4,
        "completion_tokens": 2,
        "latency_ms": 12.5,
        "total_tokens": 6,
    }


def test_inference_store_remains_compatible_with_platform_run_store(tmp_path: Path) -> None:
    db_path = tmp_path / "runs.db"
    store = InferenceStore(db_path)
    record = InferenceRecord(
        id="run-compat",
        created_at=456.0,
        model_id="model-x",
        messages=[{"role": "user", "content": "test"}],
        response="ok",
        prompt_tokens=10,
        completion_tokens=3,
        latency_ms=22.0,
    )

    store.save(record)

    compat_loaded = store.get("run-compat")
    assert compat_loaded is not None
    assert compat_loaded.to_dict() == record.to_dict()

    run_store = RunStore(db_path)
    loaded = run_store.get("run-compat")
    assert loaded is not None
    assert loaded.kind == "inference"
    assert loaded.output == {"response": "ok"}
    assert loaded.metrics == {
        "prompt_tokens": 10,
        "completion_tokens": 3,
        "latency_ms": 22.0,
        "total_tokens": 13,
    }
