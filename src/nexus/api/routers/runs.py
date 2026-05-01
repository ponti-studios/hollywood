from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from nexus.api.store import InferenceStore

router = APIRouter(prefix="/runs", tags=["runs"])


def _store(request: Request) -> InferenceStore:
    return request.app.state.store


@router.get("")
def list_runs(
    request: Request,
    model_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    return [r.to_dict() for r in _store(request).list(model_id=model_id, limit=limit, offset=offset)]


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> dict:
    record = _store(request).get(run_id)
    if record is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    return record.to_dict()


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, request: Request) -> None:
    if not _store(request).delete(run_id):
        raise HTTPException(404, f"Run '{run_id}' not found.")
