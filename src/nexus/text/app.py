from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import torch
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from nexus.api.backends import DEFAULT_TEXT_MODEL_ID
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


def _trim_stop(text: str, stop: list[str] | None) -> str:
    sequences = stop if stop is not None else ["<end_of_turn>", "<eos>", "</s>"]
    for seq in sequences:
        idx = text.find(seq)
        if idx != -1:
            text = text[:idx]
    return text.rstrip()


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


def _load_model(model_id: str) -> LoadedModel:
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=torch.float32,
    )
    model.eval()
    return LoadedModel(model_id=model_id, model=model, tokenizer=tokenizer)


def _prompt_from_messages(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            pass
    return (
        "\n".join(f"{message['role'].upper()}: {message['content']}" for message in messages)
        + "\nASSISTANT:"
    )


def _generate_text(entry: LoadedModel, body: ChatCompletionRequest) -> tuple[str, int, int]:
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    prompt = _prompt_from_messages(entry.tokenizer, messages)

    input_ids = entry.tokenizer(prompt, return_tensors="pt")
    streamer = TextIteratorStreamer(
        entry.tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    generation_kwargs = {
        "input_ids": input_ids["input_ids"],
        "attention_mask": input_ids.get("attention_mask"),
        "max_new_tokens": body.max_tokens,
        "do_sample": body.temperature > 0,
        "temperature": body.temperature if body.temperature > 0 else None,
        "pad_token_id": entry.tokenizer.pad_token_id,
        "eos_token_id": entry.tokenizer.eos_token_id,
        "streamer": streamer,
    }

    def _run() -> None:
        with torch.inference_mode():
            entry.model.generate(
                **{key: value for key, value in generation_kwargs.items() if value is not None}
            )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    completion = "".join(token for token in streamer)
    thread.join()
    completion = _trim_stop(completion, body.stop)

    prompt_tokens = len(entry.tokenizer.encode(prompt))
    completion_tokens = len(entry.tokenizer.encode(completion))
    return completion, prompt_tokens, completion_tokens


def create_app(default_model_id: str = DEFAULT_TEXT_MODEL_ID, autoload: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if autoload:
            model = await asyncio.to_thread(_load_model, default_model_id)
            app.state.models[default_model_id] = model
        yield
        app.state.models.clear()

    app = FastAPI(title="Nexus Text Service", version="0.1.0", lifespan=lifespan)
    app.state.models = {}
    app.state.default_model_id = default_model_id
    app.state.autoload = autoload
    router = APIRouter(tags=["text"])

    @router.get("/health")
    def health(request: Request) -> dict[str, object]:
        return {"ok": True, "models": list(_models(request))}

    @router.get("/models", response_model=ModelsResponse)
    def list_models(request: Request) -> ModelsResponse:
        return ModelsResponse(data=[ModelInfo(id=mid) for mid in _models(request)])

    @router.post("/models/load")
    async def load_model(body: LoadModelRequest, request: Request) -> dict[str, str]:
        models = _models(request)
        if body.model_id in models:
            return {"status": "already_loaded", "model_id": body.model_id}

        models[body.model_id] = await asyncio.to_thread(_load_model, body.model_id)
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
        entry = _get_or_404(request, body.model)

        if body.stream:
            return StreamingResponse(
                _stream_chat(entry, body),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        response_text, prompt_tokens, completion_tokens = await asyncio.to_thread(
            _generate_text,
            entry,
            body,
        )

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
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

    async def _stream_chat(entry: LoadedModel, body: ChatCompletionRequest):
        messages = [{"role": m.role, "content": m.content} for m in body.messages]
        prompt = _prompt_from_messages(entry.tokenizer, messages)
        input_ids = entry.tokenizer(prompt, return_tensors="pt")
        streamer = TextIteratorStreamer(
            entry.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())

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

        def _run() -> None:
            with torch.inference_mode():
                entry.model.generate(
                    input_ids=input_ids["input_ids"],
                    attention_mask=input_ids.get("attention_mask"),
                    max_new_tokens=body.max_tokens,
                    do_sample=body.temperature > 0,
                    pad_token_id=entry.tokenizer.pad_token_id,
                    eos_token_id=entry.tokenizer.eos_token_id,
                    streamer=streamer,
                    **({"temperature": body.temperature} if body.temperature > 0 else {}),
                )

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        for text in streamer:
            yield _chunk({"content": text})

        thread.join()
        yield _chunk({}, finish_reason="stop")

    app.include_router(router, prefix="/v1")
    return app


app = create_app()
