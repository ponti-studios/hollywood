from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from nexus.api.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    LoadModelRequest,
    ModelInfo,
    ModelsResponse,
    Usage,
)
from nexus.api.store import InferenceRecord, InferenceStore


def _store(request: Request) -> InferenceStore:
    return request.app.state.store


_DEFAULT_STOP = ["<end_of_turn>", "<eos>", "</s>"]


def _trim_stop(text: str, stop: list[str] | None) -> str:
    sequences = stop if stop is not None else _DEFAULT_STOP
    for seq in sequences:
        idx = text.find(seq)
        if idx != -1:
            text = text[:idx]
    return text.rstrip()


router = APIRouter(tags=["inference"])


@dataclass
class LoadedModel:
    model_id: str
    model: Any
    tokenizer: Any


def _models(request: Request) -> dict[str, LoadedModel]:
    return request.app.state.models


def _get_or_404(request: Request, model_id: str) -> LoadedModel:
    models = _models(request)
    if model_id not in models:
        raise HTTPException(404, f"Model '{model_id}' is not loaded. POST /v1/models/load first.")
    return models[model_id]


def _require_mlx() -> tuple[Any, Any]:
    try:
        from mlx_lm import generate, load  # noqa: F401
        return generate, load
    except ImportError:
        raise HTTPException(503, "mlx-lm is not installed. Run: pip install 'nexus[mlx]'")


def _make_sampler(temperature: float):
    from mlx_lm.sample_utils import make_sampler
    return make_sampler(temp=temperature)


@router.get("/models", response_model=ModelsResponse)
def list_models(request: Request) -> ModelsResponse:
    return ModelsResponse(data=[ModelInfo(id=mid) for mid in _models(request)])


@router.post("/models/load")
async def load_model(body: LoadModelRequest, request: Request) -> dict[str, str]:
    _, load = _require_mlx()

    models = _models(request)
    if body.model_id in models:
        return {"status": "already_loaded", "model_id": body.model_id}

    model, tokenizer = await asyncio.to_thread(load, body.model_id)
    models[body.model_id] = LoadedModel(model_id=body.model_id, model=model, tokenizer=tokenizer)
    return {"status": "loaded", "model_id": body.model_id}


@router.delete("/models/{model_id}")
def unload_model(model_id: str, request: Request) -> dict[str, str]:
    models = _models(request)
    if model_id not in models:
        raise HTTPException(404, f"Model '{model_id}' is not loaded.")
    del models[model_id]
    return {"status": "unloaded", "model_id": model_id}


@router.post("/chat/completions")
async def chat_completions(body: ChatCompletionRequest, request: Request):
    generate, _ = _require_mlx()
    entry = _get_or_404(request, body.model)

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    prompt: str = entry.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    messages_raw = [{"role": m.role, "content": m.content} for m in body.messages]

    if body.stream:
        return StreamingResponse(
            _stream_chat(entry, prompt, body, messages_raw, _store(request)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    t0 = time.perf_counter()
    response_text: str = await asyncio.to_thread(
        generate,
        entry.model,
        entry.tokenizer,
        prompt=prompt,
        max_tokens=body.max_tokens,
        sampler=_make_sampler(body.temperature),
        verbose=False,
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    response_text = _trim_stop(response_text, body.stop)

    prompt_tokens = len(entry.tokenizer.encode(prompt))
    completion_tokens = len(entry.tokenizer.encode(response_text))

    run_id = uuid.uuid4().hex
    _store(request).save(InferenceRecord(
        id=run_id,
        created_at=time.time(),
        model_id=body.model,
        messages=messages_raw,
        response=response_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=round(latency_ms, 2),
    ))

    return ChatCompletionResponse(
        id=f"chatcmpl-{run_id}",
        model=body.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


async def _stream_chat(
    entry: LoadedModel,
    prompt: str,
    body: ChatCompletionRequest,
    messages_raw: list[dict],
    store: InferenceStore,
) -> AsyncGenerator[str, None]:
    from mlx_lm import stream_generate

    run_id = uuid.uuid4().hex
    completion_id = f"chatcmpl-{run_id}"
    created = int(time.time())
    t0 = time.perf_counter()
    accumulated: list[str] = []

    def _chunk(delta: dict, finish_reason: str | None = None) -> str:
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": body.model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(payload)}\n\n"

    yield _chunk({"role": "assistant", "content": ""})

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _generate() -> None:
        try:
            for chunk in stream_generate(
                entry.model,
                entry.tokenizer,
                prompt=prompt,
                max_tokens=body.max_tokens,
                sampler=_make_sampler(body.temperature),
            ):
                text = chunk.text if hasattr(chunk, "text") else str(chunk)
                loop.call_soon_threadsafe(queue.put_nowait, text)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _generate)

    while True:
        text = await queue.get()
        if text is None:
            break
        accumulated.append(text)
        yield _chunk({"content": text})

    yield _chunk({}, finish_reason="stop")
    yield "data: [DONE]\n\n"

    full_response = _trim_stop("".join(accumulated), body.stop)
    latency_ms = (time.perf_counter() - t0) * 1000
    prompt_tokens = len(entry.tokenizer.encode(prompt))
    completion_tokens = len(entry.tokenizer.encode(full_response))
    store.save(InferenceRecord(
        id=run_id,
        created_at=float(created),
        model_id=body.model,
        messages=messages_raw,
        response=full_response,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=round(latency_ms, 2),
    ))
