from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

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
from nexus.audio.models import (
    AudioGenRequest,
    AudioHealthResponse,
    AudioSttResponse,
    AudioTtsResponse,
)
from nexus.audio.service import AudioService, AudioServiceError
from nexus.env import get_settings
from nexus.providers.openai import OpenAIClient, OpenAIError, get_openai_client

CAPABILITIES = ["text", "audio", "image", "evals"]
TEXT_ANALYZE_SYSTEM_PROMPT = (
    "You clean calendar-style text and extract people names. Return only valid JSON with keys "
    "cleaned_text and people. cleaned_text should remove person names while preserving the main "
    "activity. people should be a deduplicated list of person names mentioned in the text. No markdown."
)
AUDIO_DIR = get_settings().nexus_audio_dir
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.openai = get_openai_client()
    app.state.audio_service = AudioService(client=app.state.openai)
    yield
    await app.state.openai.aclose()


app = FastAPI(
    title="Nexus API",
    version="0.1.0",
    summary="OpenAI-first multimodal API adapter and eval layer.",
    description="Nexus routes text, audio, and image workloads through OpenAI and keeps evals separate.",
    lifespan=lifespan,
)

app.mount("/audio/files", StaticFiles(directory=AUDIO_DIR), name="audio-files")


class TextAnalysisError(RuntimeError):
    """Raised when batch text analysis output cannot be parsed."""


async def _analyze_text_item(
    *,
    openai: OpenAIClient,
    text: str,
    model: str | None,
) -> tuple[TextAnalyzeItem, int | None, int | None]:
    result = await openai.reply(
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
        raise TextAnalysisError("OpenAI did not return a JSON object for text analysis.")

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
    openai: OpenAIClient = request.app.state.openai
    audio_service: AudioService = request.app.state.audio_service
    text_ok = await openai.health()
    audio_health = audio_service.health()
    return ApiHealthResponse(
        ok=text_ok and bool(audio_health["ok"]),
        capabilities=CAPABILITIES,
        providers={"openai": text_ok, **audio_health["providers"]},
        models={
            "text": openai.text_model,
            "audio_tts": openai.tts_model,
            "audio_stt": openai.stt_model,
            "image": openai.image_model,
        },
    )


@app.get("/audio/health", response_model=AudioHealthResponse)
async def audio_health(request: Request) -> AudioHealthResponse:
    audio_service: AudioService = request.app.state.audio_service
    return AudioHealthResponse.model_validate(audio_service.health())


@app.post("/text/reply", response_model=TextReplyResponse)
async def text_reply(body: TextReplyRequest, request: Request) -> TextReplyResponse:
    openai: OpenAIClient = request.app.state.openai
    try:
        result = await openai.reply(
            prompt=body.prompt,
            model=body.model,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TextReplyResponse(
        text=result.text,
        model=result.model,
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/text/chat", response_model=TextChatResponse)
async def text_chat(body: TextChatRequest, request: Request) -> TextChatResponse:
    openai: OpenAIClient = request.app.state.openai
    messages = [message.model_dump() for message in body.messages]
    try:
        result = await openai.chat(
            messages=messages,
            model=body.model,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TextChatResponse(
        message=ChatMessage(role="assistant", content=result.text),
        model=result.model,
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/text/analyze", response_model=TextAnalyzeResponse)
async def text_analyze(body: TextAnalyzeRequest, request: Request) -> TextAnalyzeResponse:
    openai: OpenAIClient = request.app.state.openai
    try:
        analyses = await asyncio.gather(
            *[_analyze_text_item(openai=openai, text=text, model=body.model) for text in body.texts]
        )
    except (OpenAIError, TextAnalysisError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prompt_tokens = _sum_optional(value[1] for value in analyses)
    completion_tokens = _sum_optional(value[2] for value in analyses)
    results = [value[0] for value in analyses]
    model = body.model or openai.text_model
    return TextAnalyzeResponse(
        results=results,
        model=model,
        usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


@app.post("/image/analyze", response_model=ImageAnalyzeResponse)
async def image_analyze(
    request: Request,
    image: UploadFile = File(...),
    prompt: str = Form("Describe this image."),
    model: str | None = Form(None),
) -> ImageAnalyzeResponse:
    openai: OpenAIClient = request.app.state.openai
    try:
        data = await image.read()
        result = await openai.analyze_image(
            image_bytes=data,
            mime_type=image.content_type or "image/png",
            prompt=prompt,
            model=model,
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ImageAnalyzeResponse(
        text=result.text,
        model=result.model,
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/audio/tts", response_model=AudioTtsResponse)
async def audio_tts(body: AudioGenRequest, request: Request) -> AudioTtsResponse:
    audio_service: AudioService = request.app.state.audio_service
    try:
        artifact = await audio_service.tts(body)
    except AudioServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AudioTtsResponse(
        audio_url=f"/audio/files/{artifact.filename}",
        filename=artifact.filename,
        model=artifact.model,
        voice=artifact.voice,
        duration_seconds=artifact.duration_seconds,
    )


@app.post("/audio/stt", response_model=AudioSttResponse)
async def audio_stt(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("auto"),
    enhance: bool = Form(False),
) -> AudioSttResponse:
    audio_service: AudioService = request.app.state.audio_service
    try:
        payload = await file.read()
        return await audio_service.stt(
            file_bytes=payload,
            content_type=file.content_type or "application/octet-stream",
            language=language,
            enhance=enhance,
        )
    except AudioServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
async def index() -> JSONResponse:
    return JSONResponse(
        {
            "service": "nexus",
            "capabilities": CAPABILITIES,
            "docs_url": "/docs",
            "health_url": "/health",
        }
    )
