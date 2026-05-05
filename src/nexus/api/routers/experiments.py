from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nexus.evaluation import EvaluationStore
from nexus.evaluation.schema import EvaluationSchema
from nexus.experiments import ExperimentStore
from nexus.experiments.config import (
    BenchmarkSpec,
    ExperimentConfig,
    LoggingSpec,
    ModelSpec,
    SyntheticPuzzleSpec,
)
from nexus.experiments.schema import ExperimentSchema, ExperimentVariantSchema

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _store(request: Request) -> ExperimentStore:
    return request.app.state.experiment_store


def _evaluation_store(request: Request) -> EvaluationStore:
    return request.app.state.evaluation_store


# ── Request / response models ──────────────────────────────────────────────────

class RunExperimentRequest(BaseModel):
    config: ExperimentConfig | None = None
    config_path: str | None = None
    phase: int = 1
    small_model: str = "google/gemma-4-e2b"
    large_model: str | None = None
    samples: int = 500
    no_wandb: bool = False


class ExperimentRunResponse(BaseModel):
    id: str
    status: str
    config_name: str
    phase: int
    started_at: float
    completed_at: float | None = None
    output_dir: str | None = None
    error: str | None = None


class ExperimentResultsResponse(ExperimentRunResponse):
    scores: dict[str, Any] | None = None


def _summary_value(record: ExperimentSchema, key: str) -> Any:
    if not record.summary:
        return None
    return record.summary.get(key)


def _to_response(record: ExperimentSchema) -> ExperimentRunResponse:
    error_payload = record.error or {}
    return ExperimentRunResponse(
        id=record.id,
        status=record.status,
        config_name=record.name,
        phase=int(record.config.get("phase", 1)),
        started_at=record.started_at or record.created_at,
        completed_at=record.completed_at,
        output_dir=_summary_value(record, "output_dir"),
        error=error_payload.get("traceback") or error_payload.get("message"),
    )


def _capability_for_experiment(cfg: ExperimentConfig) -> str:
    return "text"


def _variant_specs_from_config(
    cfg: ExperimentConfig,
) -> list[ExperimentVariantSchema]:
    # Benchmark experiment variants: one per model spec.
    variants: list[ExperimentVariantSchema] = []
    for index, model in enumerate(cfg.models, start=1):
        variants.append(
            ExperimentVariantSchema(
                id=f"{model.role}-{index}",
                model_id=model.model_id,
                config=model.model_dump(mode="json"),
            )
        )
    return variants

def _experiment_from_config(
    cfg: ExperimentConfig,
    experiment_id: str,
) -> ExperimentSchema:
    created_at = time.time()
    return ExperimentSchema(
        id=experiment_id,
        name=cfg.name,
        hypothesis=cfg.description or f"Phase {cfg.phase} experiment",
        capability=_capability_for_experiment(cfg),
        status="pending",
        benchmark_ids=[benchmark.name for benchmark in cfg.benchmarks],
        variant_specs=_variant_specs_from_config(cfg),
        run_ids=[],
        evaluation_ids=[],
        config=cfg.model_dump(mode="json"),
        summary={"phase": cfg.phase},
        winner=None,
        error=None,
        created_at=created_at,
        started_at=created_at,
        completed_at=None,
    )

def _evaluation_records_for_scores(
    experiment: ExperimentSchema,
    score_payload: dict[str, dict[str, Any]],
    scorer: str = "benchmark_score",
) -> list[EvaluationSchema]:
    created_at = time.time()
    records: list[EvaluationSchema] = []
    for variant_key, metrics in score_payload.items():
        records.append(
            EvaluationSchema(
                id=uuid.uuid4().hex,
                subject_type="experiment",
                subject_id=experiment.id,
                capability=experiment.capability,
                benchmark_id=variant_key,
                scorer=scorer,
                rubric=f"phase-{experiment.config.get('phase', 0)}-{scorer}",
                metrics=metrics,
                judgment=metrics.get("accuracy_pct") or metrics.get("pass_rate_pct"),
                notes=f"Stored from experiment {experiment.name}",
                created_at=created_at,
            )
        )
    return records


# ── Config type detection ─────────────────────────────────────────────────────

def _load_config_from_path(path: Path) -> ExperimentConfig:
    """Load a benchmark YAML config file."""
    with open(path) as f:
        import yaml
        raw = yaml.safe_load(f)
    return ExperimentConfig(**raw)


# ── Runner factory ─────────────────────────────────────────────────────────────

def _build_config(body: RunExperimentRequest) -> ExperimentConfig:
    if body.config is not None:
        return body.config

    if body.config_path is not None:
        path = Path(body.config_path)
        if not path.exists():
            raise HTTPException(400, f"Config file not found: {body.config_path}")
        return _load_config_from_path(path)

    models: list[ModelSpec] = [ModelSpec(model_id=body.small_model, role="small")]
    if body.large_model:
        models.append(ModelSpec(model_id=body.large_model, role="large"))

    return ExperimentConfig(
        name=f"exp_phase{body.phase}_{uuid.uuid4().hex[:6]}",
        description=f"Phase {body.phase} experiment",
        phase=body.phase,  # type: ignore[arg-type]
        models=models,
        benchmarks=[
            BenchmarkSpec(name="triviaqa", samples=body.samples),
            BenchmarkSpec(name="mmlu", samples=body.samples),
            BenchmarkSpec(name="synthetic", samples=body.samples),
        ],
        synthetic=SyntheticPuzzleSpec(),
        logging=LoggingSpec(wandb_project=None if body.no_wandb else "nexus"),
    )


def _runner_for(cfg: ExperimentConfig):
    if cfg.phase == 1:
        from nexus.experiments.phases.baseline import BaselineRunner
        return BaselineRunner(cfg)
    if cfg.phase == 2:
        from nexus.experiments.phases.open_book import OpenBookRunner
        return OpenBookRunner(cfg)
    if cfg.phase == 3:
        from nexus.experiments.phases.reflection import ReflectionRunner
        return ReflectionRunner(cfg)
    raise HTTPException(400, f"Phase {cfg.phase} is not yet implemented.")


# ── Background execution ───────────────────────────────────────────────────────

async def _execute(
    experiment_id: str,
    cfg: ExperimentConfig,
    store: ExperimentStore,
    evaluation_store: EvaluationStore,
) -> None:
    current = store.get(experiment_id)
    if current is None:
        return

    running = current.model_copy(update={"status": "running"})
    store.save(running)

    try:
        runner = _runner_for(cfg)
        scores = await asyncio.to_thread(runner.execute)
        score_payload = {key: value.to_dict() for key, value in scores.items()}

        evaluations = _evaluation_records_for_scores(running, score_payload, "benchmark_score")
        for evaluation in evaluations:
            evaluation_store.save(evaluation)

        completed = running.model_copy(
            update={
                "status": "completed",
                "evaluation_ids": [evaluation.id for evaluation in evaluations],
                "summary": {
                    **(running.summary or {}),
                    "phase": cfg.phase,
                    "output_dir": str(cfg.output_path()),
                    "scores": score_payload,
                },
                "completed_at": time.time(),
            }
        )
        store.save(completed)
    except Exception:
        failed = running.model_copy(
            update={
                "status": "failed",
                "error": {"traceback": traceback.format_exc()},
                "summary": {
                    **(running.summary or {}),
                    "phase": cfg.phase,
                },
                "completed_at": time.time(),
            }
        )
        store.save(failed)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ExperimentRunResponse, status_code=202)
async def submit_experiment(body: RunExperimentRequest, request: Request) -> ExperimentRunResponse:
    cfg = _build_config(body)
    experiment = _experiment_from_config(cfg, uuid.uuid4().hex)
    store = _store(request)
    store.save(experiment)
    asyncio.create_task(_execute(experiment.id, cfg, store, _evaluation_store(request)))
    return _to_response(experiment)


@router.get("", response_model=list[ExperimentRunResponse])
def list_experiments(
    request: Request,
    capability: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ExperimentRunResponse]:
    return [
        _to_response(record)
        for record in _store(request).list(
            capability=capability,
            status=status,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/{experiment_id}", response_model=ExperimentRunResponse)
def get_experiment(experiment_id: str, request: Request) -> ExperimentRunResponse:
    record = _store(request).get(experiment_id)
    if record is None:
        raise HTTPException(404, f"Experiment '{experiment_id}' not found.")
    return _to_response(record)


@router.get("/{experiment_id}/results", response_model=ExperimentResultsResponse)
def get_results(experiment_id: str, request: Request) -> ExperimentResultsResponse:
    record = _store(request).get(experiment_id)
    if record is None:
        raise HTTPException(404, f"Experiment '{experiment_id}' not found.")
    if record.status == "running":
        raise HTTPException(425, "Experiment is still running.")
    return ExperimentResultsResponse(
        **_to_response(record).model_dump(),
        scores=_summary_value(record, "scores"),
    )


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str, request: Request) -> None:
    record = _store(request).get(experiment_id)
    if record is None:
        raise HTTPException(404, f"Experiment '{experiment_id}' not found.")
    if record.status == "running":
        raise HTTPException(409, "Cannot delete a running experiment.")
    _store(request).delete(experiment_id)
