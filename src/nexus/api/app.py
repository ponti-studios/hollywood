from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from nexus.api.backends import ApiBackends
from nexus.api.models import ApiHealthResponse
from nexus.api.routers import audio, experiments, inference, runs
from nexus.api.store import InferenceStore
from nexus.evaluation import EvaluationStore
from nexus.experiments import ExperimentStore
from nexus.runs import RunStore

OPENAPI_TAGS = [
    {
        "name": "text",
        "description": "Text generation routes.",
    },
    {
        "name": "audio",
        "description": "Audio synthesis, transcription, and backend health routes.",
    },
    {
        "name": "experiments",
        "description": "Experiment submission, tracking, and results routes.",
    },
    {
        "name": "runs",
        "description": "Platform run ledger routes.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.backends = ApiBackends.default()
    app.state.run_store = RunStore(Path(".data/api/inference.db"))
    app.state.inference_store = InferenceStore(Path(".data/api/inference.db"))
    app.state.experiment_store = ExperimentStore(Path(".data/api/inference.db"))
    app.state.evaluation_store = EvaluationStore(Path(".data/api/inference.db"))
    app.state.model_backends = {
        app.state.backends.text_model_id: app.state.backends.text_model_url,
    }
    yield


app = FastAPI(
    title="Nexus API",
    version="0.1.0",
    summary="Public control plane for Nexus text, audio, runs, and experiments.",
    description=(
        "Nexus exposes a small public API that fronts private text and audio workers. "
        "Use the generated OpenAPI schema at /openapi.json or the interactive docs at /docs."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.include_router(inference.router, prefix="/v1")
app.include_router(audio.router, prefix="/v1")
app.include_router(experiments.router, prefix="/v1")
app.include_router(runs.router, prefix="/v1")


@app.get("/health", response_model=ApiHealthResponse)
def health() -> ApiHealthResponse:
    return ApiHealthResponse(
        ok=True,
        service="nexus",
        api="control-plane",
        capabilities=["text", "audio", "experiments", "runs"],
    )


@app.get("/", include_in_schema=False)
def index() -> dict[str, object]:
    return {
        "service": "nexus",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "capabilities": ["text", "audio", "experiments", "runs"],
    }
