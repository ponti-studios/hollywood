from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from nexus.api.models import (
    ApiHealthResponse,
    ChatMessage,
    ImageAnalyzeResponse,
    TextChatRequest,
    TextChatResponse,
    TextReplyRequest,
    TextReplyResponse,
    Usage,
)
from nexus.audio.models import AudioGenRequest, AudioHealthResponse, AudioSttResponse, AudioTtsResponse
from nexus.audio.service import AudioService, AudioServiceError
from nexus.providers.gemini import GeminiClient, GeminiError, get_gemini_client

CAPABILITIES = ["text", "audio", "image", "evals"]
AUDIO_DIR = Path(".data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.gemini = get_gemini_client()
    app.state.audio_service = AudioService(client=app.state.gemini)
    yield
    await app.state.gemini.aclose()


app = FastAPI(
    title="Nexus API",
    version="0.1.0",
    summary="Gemini-first multimodal API adapter and eval layer.",
    description="Nexus routes text, audio, and image workloads through Gemini and keeps evals separate.",
    lifespan=lifespan,
)

app.mount("/audio/files", StaticFiles(directory=AUDIO_DIR), name="audio-files")


@app.get("/health", response_model=ApiHealthResponse)
async def health(request: Request) -> ApiHealthResponse:
    gemini: GeminiClient = request.app.state.gemini
    audio_service: AudioService = request.app.state.audio_service
    text_ok = await gemini.health()
    audio_health = audio_service.health()
    return ApiHealthResponse(
        ok=text_ok and bool(audio_health["ok"]),
        capabilities=CAPABILITIES,
        providers={"gemini": text_ok, **audio_health["providers"]},
        models={
            "text": gemini.text_model,
            "audio": gemini.audio_model,
            "image": gemini.image_model,
        },
    )


@app.get("/audio/health", response_model=AudioHealthResponse)
async def audio_health(request: Request) -> AudioHealthResponse:
    audio_service: AudioService = request.app.state.audio_service
    return AudioHealthResponse.model_validate(audio_service.health())


@app.post("/text/reply", response_model=TextReplyResponse)
async def text_reply(body: TextReplyRequest, request: Request) -> TextReplyResponse:
    gemini: GeminiClient = request.app.state.gemini
    try:
        result = await gemini.reply(
            prompt=body.prompt,
            model=body.model,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
        )
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TextReplyResponse(
        text=result.text,
        model=result.model,
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/text/chat", response_model=TextChatResponse)
async def text_chat(body: TextChatRequest, request: Request) -> TextChatResponse:
    gemini: GeminiClient = request.app.state.gemini
    messages = [message.model_dump() for message in body.messages]
    try:
        result = await gemini.chat(
            messages=messages,
            model=body.model,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
        )
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TextChatResponse(
        message=ChatMessage(role="assistant", content=result.text),
        model=result.model,
        usage=Usage(prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens),
    )


@app.post("/image/analyze", response_model=ImageAnalyzeResponse)
async def image_analyze(
    request: Request,
    image: UploadFile = File(...),
    prompt: str = Form("Describe this image."),
    model: str | None = Form(None),
) -> ImageAnalyzeResponse:
    gemini: GeminiClient = request.app.state.gemini
    try:
        data = await image.read()
        result = await gemini.analyze_image(
            image_bytes=data,
            mime_type=image.content_type or "image/png",
            prompt=prompt,
            model=model,
        )
    except GeminiError as exc:
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
