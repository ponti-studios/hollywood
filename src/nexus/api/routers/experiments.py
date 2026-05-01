from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nexus.experiments.config import (
    BenchmarkSpec,
    ExperimentConfig,
    LoggingSpec,
    ModelSpec,
    SyntheticPuzzleSpec,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


# ── In-memory run state ────────────────────────────────────────────────────────

@dataclass
class ExperimentRun:
    id: str
    status: Literal["pending", "running", "completed", "failed"]
    config: ExperimentConfig
    started_at: float
    completed_at: float | None = None
    scores: dict[str, Any] | None = None
    output_dir: str | None = None
    error: str | None = None


def _runs(request: Request) -> dict[str, ExperimentRun]:
    return request.app.state.experiments


# ── Request / response models ──────────────────────────────────────────────────

class RunExperimentRequest(BaseModel):
    config: ExperimentConfig | None = None
    config_path: str | None = None
    phase: int = 1
    small_model: str = "google/gemma-3-4b-it"
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


def _to_response(run: ExperimentRun) -> ExperimentRunResponse:
    return ExperimentRunResponse(
        id=run.id,
        status=run.status,
        config_name=run.config.name,
        phase=run.config.phase,
        started_at=run.started_at,
        completed_at=run.completed_at,
        output_dir=run.output_dir,
        error=run.error,
    )


# ── Runner factory ─────────────────────────────────────────────────────────────

def _build_config(body: RunExperimentRequest) -> ExperimentConfig:
    if body.config is not None:
        return body.config

    if body.config_path is not None:
        path = Path(body.config_path)
        if not path.exists():
            raise HTTPException(400, f"Config file not found: {body.config_path}")
        return ExperimentConfig.from_yaml(path)

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

async def _execute(run: ExperimentRun) -> None:
    run.status = "running"
    try:
        runner = _runner_for(run.config)
        scores = await asyncio.to_thread(runner.execute)
        run.scores = {k: v.to_dict() for k, v in scores.items()}
        run.output_dir = str(run.config.output_path())
        run.status = "completed"
    except Exception:
        run.error = traceback.format_exc()
        run.status = "failed"
    finally:
        run.completed_at = time.time()


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ExperimentRunResponse, status_code=202)
async def submit_experiment(body: RunExperimentRequest, request: Request) -> ExperimentRunResponse:
    cfg = _build_config(body)
    run = ExperimentRun(
        id=uuid.uuid4().hex,
        status="pending",
        config=cfg,
        started_at=time.time(),
    )
    _runs(request)[run.id] = run
    asyncio.create_task(_execute(run))
    return _to_response(run)


@router.get("", response_model=list[ExperimentRunResponse])
def list_experiments(request: Request) -> list[ExperimentRunResponse]:
    return [_to_response(r) for r in _runs(request).values()]


@router.get("/{run_id}", response_model=ExperimentRunResponse)
def get_experiment(run_id: str, request: Request) -> ExperimentRunResponse:
    run = _runs(request).get(run_id)
    if run is None:
        raise HTTPException(404, f"Experiment run '{run_id}' not found.")
    return _to_response(run)


@router.get("/{run_id}/results", response_model=ExperimentResultsResponse)
def get_results(run_id: str, request: Request) -> ExperimentResultsResponse:
    run = _runs(request).get(run_id)
    if run is None:
        raise HTTPException(404, f"Experiment run '{run_id}' not found.")
    if run.status == "running":
        raise HTTPException(425, "Experiment is still running.")
    return ExperimentResultsResponse(
        **_to_response(run).model_dump(),
        scores=run.scores,
    )


@router.delete("/{run_id}", status_code=204)
def delete_experiment(run_id: str, request: Request) -> None:
    runs = _runs(request)
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(404, f"Experiment run '{run_id}' not found.")
    if run.status == "running":
        raise HTTPException(409, "Cannot delete a running experiment.")
    del runs[run_id]
