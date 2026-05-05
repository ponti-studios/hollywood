from __future__ import annotations

from nexus.artifacts.schema import ArtifactSchema
from nexus.evaluation.schema import EvaluationSchema
from nexus.experiments.schema import ExperimentSchema, ExperimentVariantSchema
from nexus.jobs.schema import JobSchema
from nexus.runs.schema import RunSchema


def test_run_schema_validates_platform_run_payload() -> None:
    payload = {
        "id": "run_123",
        "kind": "inference",
        "capability": "text",
        "status": "completed",
        "model_id": "model-a",
        "input": {"messages": [{"role": "user", "content": "hi"}]},
        "output": {"response": "hello"},
        "config": {"temperature": 0.7},
        "metrics": {"latency_ms": 12.5},
        "artifact_ids": [],
        "error": None,
        "started_at": 1.0,
        "completed_at": 2.0,
        "created_at": 2.0,
        "messages": [{"role": "user", "content": "hi"}],
        "response": "hello",
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "latency_ms": 12.5,
    }

    schema = RunSchema.model_validate(payload)
    assert schema.id == "run_123"
    assert schema.kind == "inference"
    assert schema.response == "hello"


def test_job_evaluation_experiment_and_artifact_schemas_validate_payloads() -> None:
    job = JobSchema(
        id="job_123",
        kind="training",
        capability="text",
        status="queued",
        created_at=1.0,
    )
    evaluation = EvaluationSchema(
        id="eval_123",
        subject_type="run",
        subject_id="run_123",
        capability="audio",
        scorer="judge:gpt-4.1",
        created_at=1.0,
    )
    experiment = ExperimentSchema(
        id="exp_123",
        name="compare-variants",
        hypothesis="A beats B",
        capability="audio",
        status="pending",
        variant_specs=[ExperimentVariantSchema(id="a"), ExperimentVariantSchema(id="b")],
        created_at=1.0,
    )
    artifact = ArtifactSchema(
        id="art_123",
        kind="audio",
        capability="audio",
        uri=".data/audio/out.wav",
        created_at=1.0,
    )

    assert job.kind == "training"
    assert evaluation.subject_type == "run"
    assert experiment.variant_specs[0].id == "a"
    assert artifact.kind == "audio"
