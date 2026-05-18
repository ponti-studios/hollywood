from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile

from nexus.api.models import (
    ApiHealthResponse,
    ChatMessage,
    ImageAnalyzeResponse,
    TextAnalyzeItem,
    TextAnalyzeRequest,
    TextAnalyzeResponse,
    TextChatRequest,
    TextChatResponse,
    TextReplyRequest,
    TextReplyResponse,
    Usage,
)
from nexus.providers.openrouter import OpenRouterClient, OpenRouterError, get_openrouter_client

CAPABILITIES = ["text", "image", "evals"]
TEXT_ANALYZE_SYSTEM_PROMPT = (
    "You clean calendar-style text and extract people names. Return only valid JSON with keys "
    "cleaned_text and people. cleaned_text should remove person names while preserving the main "
    "activity. people should be a deduplicated list of person names mentioned in the text. No markdown."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.openrouter = get_openrouter_client()
    yield
    await app.state.openrouter.aclose()


app = FastAPI(
    title="Nexus API",
    version="0.1.0",
    summary="OpenRouter-first multimodal API adapter and eval layer.",
    description="Nexus routes text and image workloads through OpenRouter and keeps evals separate.",
    lifespan=lifespan,
)


class TextAnalysisError(RuntimeError):
    """Raised when batch text analysis output cannot be parsed."""


async def _analyze_text_item(
    *,
    openrouter: OpenRouterClient,
    text: str,
    model: str | None,
) -> tuple[TextAnalyzeItem, int | None, int | None]:
    result = await openrouter.reply(
        prompt=text,
        model=model,
        temperature=0.0,
        top_p=0.1,
        max_tokens=256,
        system=TEXT_ANALYZE_SYSTEM_PROMPT,
    )
    cleaned_text, people = _parse_text_analysis_payload(result.text)
    return (
        TextAnalyzeItem(input=text, cleaned_text=cleaned_text, people=people),
        result.prompt_tokens,
        result.completion_tokens,
    )


def _parse_text_analysis_payload(raw_text: str) -> tuple[str, list[str]]:
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise TextAnalysisError("OpenRouter did not return a JSON object for text analysis.")

    try:
        payload = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise TextAnalysisError(f"Could not parse text analysis JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise TextAnalysisError("Text analysis response must be a JSON object.")

    cleaned_text = payload.get("cleaned_text")
    people = payload.get("people")
    if not isinstance(cleaned_text, str) or not cleaned_text.strip():
        raise TextAnalysisError("Text analysis response is missing cleaned_text.")
    if not isinstance(people, list):
        raise TextAnalysisError("Text analysis response is missing people.")

    normalized_people: list[str] = []
    seen: set[str] = set()
    for person in people:
        if not isinstance(person, str):
            continue
        normalized = person.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_people.append(normalized)

    return cleaned_text.strip(), normalized_people


def _sum_optional(values: Iterable[int | None]) -> int | None:
    collected = [value for value in values if isinstance(value, int)]
    if not collected:
        return None
    return sum(collected)


@app.get("/health", response_model=ApiHealthResponse)
async def health(request: Request) -> ApiHealthResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    provider_ok = await openrouter.health()
    return ApiHealthResponse(
        ok=provider_ok,
        capabilities=CAPABILITIES,
        providers={"openrouter": provider_ok},
        models={"text": openrouter.text_model, "image": openrouter.image_model},
    )


@app.post("/text/reply", response_model=TextReplyResponse)
async def text_reply(body: TextReplyRequest, request: Request) -> TextReplyResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    try:
        result = await openrouter.reply(
            prompt=body.prompt,
            model=body.model,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TextReplyResponse(
        text=result.text,
        model=result.model,
        provider="openrouter",
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/text/chat", response_model=TextChatResponse)
async def text_chat(body: TextChatRequest, request: Request) -> TextChatResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    messages = [message.model_dump() for message in body.messages]
    try:
        result = await openrouter.chat(
            messages=messages,
            model=body.model,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TextChatResponse(
        message=ChatMessage(role="assistant", content=result.text),
        model=result.model,
        provider="openrouter",
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/text/analyze", response_model=TextAnalyzeResponse)
async def text_analyze(body: TextAnalyzeRequest, request: Request) -> TextAnalyzeResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    try:
        analyses = await asyncio.gather(*[
            _analyze_text_item(openrouter=openrouter, text=text, model=body.model)
            for text in body.texts
        ])
    except (OpenRouterError, TextAnalysisError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prompt_tokens = _sum_optional(value[1] for value in analyses)
    completion_tokens = _sum_optional(value[2] for value in analyses)
    results = [value[0] for value in analyses]
    model = body.model or openrouter.text_model
    return TextAnalyzeResponse(
        results=results,
        model=model,
        provider="openrouter",
        usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


@app.post("/image/analyze", response_model=ImageAnalyzeResponse)
async def image_analyze(
    request: Request,
    image: UploadFile = File(...),
    prompt: str = "Describe this image.",
    model: str | None = None,
) -> ImageAnalyzeResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    try:
        data = await image.read()
        result = await openrouter.analyze_image(
            image_bytes=data,
            mime_type=image.content_type or "image/png",
            prompt=prompt,
            model=model,
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ImageAnalyzeResponse(
        text=result.text,
        model=result.model,
        provider="openrouter",
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )
