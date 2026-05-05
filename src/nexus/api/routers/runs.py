from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from nexus.runs import RunRecord, RunStore
from nexus.runs.schema import RunSchema

router = APIRouter(prefix="/runs", tags=["runs"])


def _store(request: Request) -> RunStore:
    return request.app.state.run_store


def _to_response(record: RunRecord) -> RunSchema:
    payload = record.to_dict()
    return RunSchema(**payload)


@router.get("", response_model=list[RunSchema])
def list_runs(
    request: Request,
    kind: str | None = None,
    capability: str | None = None,
    model_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[RunSchema]:
    return [
        _to_response(r)
        for r in _store(request).list(
            kind=kind,
            capability=capability,
            model_id=model_id,
            limit=limit,
            offset=offset,
        )
    ]


@router.get("/{run_id}", response_model=RunSchema)
def get_run(run_id: str, request: Request) -> RunSchema:
    record = _store(request).get(run_id)
    if record is None:
        raise HTTPException(404, f"Run '{run_id}' not found.")
    return _to_response(record)


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, request: Request) -> None:
    if not _store(request).delete(run_id):
        raise HTTPException(404, f"Run '{run_id}' not found.")
