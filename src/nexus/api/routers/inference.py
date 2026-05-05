from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from typing import NoReturn

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from nexus.api.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from nexus.api.store import InferenceRecord, InferenceStore

router = APIRouter(tags=["text"])


def _registry(request: Request) -> dict[str, str]:
    return request.app.state.model_backends


def _store(request: Request) -> InferenceStore:
    return request.app.state.inference_store


def _raise_http(status_code: int, message: str) -> NoReturn:
    raise HTTPException(status_code=status_code, detail={"error": {"message": message}})


def _backend_url(request: Request, model_id: str) -> str:
    registry = _registry(request)
    if model_id not in registry:
        raise HTTPException(404, f"Model '{model_id}' is not available.")
    return registry[model_id]


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        200: {
            "description": "Returns a chat completion or an SSE stream when `stream=true`.",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "examples": {
                        "chunk": {
                            "summary": "Streaming chunk",
                            "value": "data: {...}\n\n",
                        }
                    },
                }
            },
        }
    },
)
async def chat_completions(body: ChatCompletionRequest, request: Request):
    backend_url = _backend_url(request, body.model)
    payload = body.model_dump()

    if body.stream:
        return StreamingResponse(
            _stream_chat(backend_url, payload),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(f"{backend_url}/v1/chat/completions", json=payload)
    if response.status_code >= 400:
        _raise_http(response.status_code, response.text)

    response_payload = response.json()
    _save_run(request, body, response_payload, time.perf_counter() - t0)
    return JSONResponse(response_payload, status_code=response.status_code)


async def _stream_chat(backend_url: str, payload: dict) -> AsyncGenerator[bytes, None]:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST", f"{backend_url}/v1/chat/completions", json=payload
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                _raise_http(response.status_code, body.decode("utf-8", errors="replace"))

            async for chunk in response.aiter_bytes():
                yield chunk


def _save_run(
    request: Request,
    body: ChatCompletionRequest,
    response_payload: dict,
    latency_seconds: float,
) -> None:
    prompt_tokens = int(response_payload.get("usage", {}).get("prompt_tokens", 0))
    completion_tokens = int(response_payload.get("usage", {}).get("completion_tokens", 0))
    response_text = ""
    try:
        response_text = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        response_text = ""

    run_id = response_payload.get("id", f"chatcmpl-{uuid.uuid4().hex}")
    _store(request).save(
        InferenceRecord(
            id=str(run_id).removeprefix("chatcmpl-"),
            created_at=float(response_payload.get("created", time.time())),
            model_id=body.model,
            messages=[message.model_dump() for message in body.messages],
            response=response_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_seconds * 1000, 2),
        )
    )
