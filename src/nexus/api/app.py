from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile

from nexus.api.models import (
    ApiHealthResponse,
    AudioSpeechRequest,
    AudioTranscribeResponse,
    AudioUsage,
    ChatMessage,
    EvalResultItem,
    EvalsRunResponse,
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
from nexus.evaluation.demo import run_demo_evals
from nexus.providers.openrouter import OpenRouterClient, OpenRouterError, get_openrouter_client

CAPABILITIES = ["text", "image", "audio", "evals"]
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


_MIME_TO_FORMAT: dict[str, str] = {
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/flac": "flac",
    "audio/mp4": "m4a",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
    "audio/aac": "aac",
}
_EXT_TO_FORMAT: dict[str, str] = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".m4a": "m4a",
    ".ogg": "ogg",
    ".webm": "webm",
    ".aac": "aac",
}


def _audio_format(content_type: str, filename: str) -> str:
    if content_type in _MIME_TO_FORMAT:
        return _MIME_TO_FORMAT[content_type]
    return _EXT_TO_FORMAT.get(Path(filename).suffix.lower(), "wav")


@app.get("/health", response_model=ApiHealthResponse)
async def health(request: Request) -> ApiHealthResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    provider_ok = await openrouter.health()
    return ApiHealthResponse(
        ok=provider_ok,
        capabilities=CAPABILITIES,
        providers={"openrouter": provider_ok},
        models={
            "text": openrouter.text_model,
            "image": openrouter.image_model,
            "tts": openrouter.tts_model,
            "stt": openrouter.stt_model,
        },
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


@app.post("/evals/run", response_model=EvalsRunResponse)
async def evals_run(model: str | None = None) -> EvalsRunResponse:
    try:
        demo_results = await run_demo_evals(model=model)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    items = [
        EvalResultItem(
            name=r.name,
            score=r.score,
            passed=r.passed,
            response=r.response,
            details=r.details,
        )
        for r in demo_results
    ]
    return EvalsRunResponse(
        results=items,
        passed=sum(1 for item in items if item.passed),
        total=len(items),
        model=model,
    )


@app.post("/audio/speech")
async def audio_speech(body: AudioSpeechRequest, request: Request) -> Response:
    openrouter: OpenRouterClient = request.app.state.openrouter
    try:
        audio_bytes = await openrouter.tts(
            text=body.text,
            voice=body.voice,
            model=body.model,
            response_format=body.response_format,
            speed=body.speed,
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    media_type = "audio/mpeg" if body.response_format == "mp3" else "audio/pcm"
    return Response(content=audio_bytes, media_type=media_type)


@app.post("/audio/transcribe", response_model=AudioTranscribeResponse)
async def audio_transcribe(
    request: Request,
    audio: UploadFile = File(...),
    model: str | None = None,
    language: str | None = None,
) -> AudioTranscribeResponse:
    openrouter: OpenRouterClient = request.app.state.openrouter
    try:
        data = await audio.read()
        audio_fmt = _audio_format(audio.content_type or "", audio.filename or "")
        result = await openrouter.stt(
            audio_bytes=data,
            audio_format=audio_fmt,
            model=model,
            language=language,
        )
    except OpenRouterError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AudioTranscribeResponse(
        text=result.text,
        model=result.model,
        provider="openrouter",
        usage=AudioUsage(
            seconds=result.seconds,
            total_tokens=result.total_tokens,
            cost=result.cost,
        ),
    )
