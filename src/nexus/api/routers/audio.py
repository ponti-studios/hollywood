from __future__ import annotations

from typing import NoReturn

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from nexus.audio import AudioGenRequest
from nexus.audio.models import AudioHealthData, AudioHealthResponse, AudioTranscriptionResponse

router = APIRouter(prefix="/audio", tags=["audio"])


def _backends(request: Request):
    return request.app.state.backends


def _raise_http(status_code: int, message: str) -> NoReturn:
    raise HTTPException(status_code=status_code, detail={"error": {"message": message}})


async def _backend_json(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url)
    if response.status_code >= 400:
        _raise_http(response.status_code, response.text)
    return response.json()


@router.get("/health", response_model=AudioHealthResponse)
async def health(request: Request) -> AudioHealthResponse:
    backends = _backends(request)
    async with httpx.AsyncClient(timeout=30.0) as client:
        tts = await _backend_json(client, f"{backends.audio_tts_url}/health")
        asr = await _backend_json(client, f"{backends.audio_asr_url}/health")
    return AudioHealthResponse(
        data=AudioHealthData(
            ok=True,
            tts=tts.get("data", tts),
            asr=asr.get("data", asr),
        ),
        role="audio",
    )


@router.post(
    "/tts",
    response_class=Response,
    responses={
        200: {
            "content": {
                "audio/wav": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
            "description": "Synthesized audio stream in WAV format.",
        }
    },
)
async def tts(body: AudioGenRequest, request: Request) -> Response:
    backends = _backends(request)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(f"{backends.audio_tts_url}/tts", json=body.model_dump())
    if response.status_code >= 400:
        _raise_http(response.status_code, response.text)
    headers = {}
    if "content-disposition" in response.headers:
        headers["Content-Disposition"] = response.headers["content-disposition"]
    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "audio/wav"),
        headers=headers,
    )


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def asr(request: Request, audio: UploadFile = File(...)) -> AudioTranscriptionResponse:
    backends = _backends(request)
    content = await audio.read()
    filename = audio.filename or "audio.wav"
    content_type = audio.content_type or "application/octet-stream"
    files = {"audio": (filename, content, content_type)}
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(f"{backends.audio_asr_url}/transcribe", files=files)
    if response.status_code >= 400:
        _raise_http(response.status_code, response.text)
    return AudioTranscriptionResponse.model_validate(response.json())
