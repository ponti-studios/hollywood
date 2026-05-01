from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from nexus.voice import ApiError, KokoroRequest, VoiceError, VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])
_service = VoiceService()


def _raise(exc: VoiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail=ApiError(code=exc.code, message=exc.message, details=exc.details).model_dump(),
    )


@router.get("/health")
def health() -> dict[str, object]:
    return {"data": _service.health()}


@router.post("/tts", response_class=FileResponse)
async def tts(request: KokoroRequest) -> FileResponse:
    try:
        output_file = await _service.kokoro_tts(request)
    except VoiceError as exc:
        _raise(exc)
    return FileResponse(output_file, media_type="audio/wav", filename=output_file.name)


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict[str, object]:
    try:
        text = await _service.transcribe(audio.filename, audio.file)
    except VoiceError as exc:
        _raise(exc)
    return {"data": {"text": text}}
