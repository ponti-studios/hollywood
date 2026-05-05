from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from nexus.audio import ApiError, AudioError, AudioGenRequest, AudioService


def _role() -> Literal["tts", "asr"]:
    value = os.getenv("NEXUS_AUDIO_ROLE", "tts").strip().lower()
    if value not in {"tts", "asr"}:
        raise ValueError("NEXUS_AUDIO_ROLE must be 'tts' or 'asr'")
    return value  # type: ignore[return-value]


def _raise(exc: AudioError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail=ApiError(code=exc.code, message=exc.message, details=exc.details).model_dump(),
    )


def create_app(role: Literal["tts", "asr"] | None = None) -> FastAPI:
    service = AudioService()
    resolved_role = role or _role()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.audio_service = service
        app.state.audio_role = resolved_role
        yield

    app = FastAPI(title="Nexus Audio Service", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"data": service.health(), "role": resolved_role}

    if resolved_role == "tts":

        @app.post("/tts", response_class=FileResponse)
        async def tts(request: AudioGenRequest) -> FileResponse:
            try:
                output_file = await service.tts(request)
            except AudioError as exc:
                _raise(exc)
            return FileResponse(output_file, media_type="audio/wav", filename=output_file.name)

    if resolved_role == "asr":

        @app.post("/transcribe")
        async def transcribe(audio: UploadFile = File(...)) -> dict[str, object]:
            try:
                text = await service.transcribe(audio.filename, audio.file)
            except AudioError as exc:
                _raise(exc)
            return {"data": {"text": text}}

    return app


app = create_app()
