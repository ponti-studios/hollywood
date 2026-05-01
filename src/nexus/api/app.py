from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from nexus.api.routers import experiments, inference, runs, voice
from nexus.api.store import InferenceStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models = {}
    app.state.experiments = {}
    app.state.store = InferenceStore(Path(".data/api/inference.db"))
    yield
    app.state.models.clear()
    app.state.experiments.clear()


app = FastAPI(title="Nexus API", version="0.1.0", lifespan=lifespan)

app.include_router(inference.router, prefix="/v1")
app.include_router(voice.router, prefix="/v1")
app.include_router(experiments.router, prefix="/v1")
app.include_router(runs.router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True}
