from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from nexus.audio.models import AudioGenRequest, AudioSttResponse
from nexus.providers.gemini import GeminiClient, GeminiError, get_gemini_client

DEFAULT_AUDIO_DIR = Path(os.getenv("NEXUS_AUDIO_DIR", ".data/audio"))


class AudioServiceError(RuntimeError):
    """Raised when Gemini audio handling fails."""


@dataclass(slots=True)
class AudioTtsArtifact:
    path: Path
    filename: str
    model: str
    voice: str
    duration_seconds: float | None


class AudioService:
    def __init__(
        self, *, audio_dir: Path | None = None, client: GeminiClient | None = None
    ) -> None:
        self.audio_dir = audio_dir or DEFAULT_AUDIO_DIR
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.client = client or get_gemini_client()

    def health(self) -> dict[str, object]:
        return {
            "ok": bool(self.client.api_key),
            "providers": {"gemini": bool(self.client.api_key)},
            "models": {"tts": self.client.audio_model, "stt": self.client.audio_model},
        }

    async def tts(self, request: AudioGenRequest) -> AudioTtsArtifact:
        if not self.client.api_key:
            raise AudioServiceError("GEMINI_API_KEY is required for text-to-speech.")

        try:
            result = await self.client.synthesize_speech(
                text=request.text,
                model=request.model or self.client.audio_model,
                voice=request.voice,
                mime_type=_mime_type_for_format(request.format),
            )
        except GeminiError as exc:
            raise AudioServiceError(str(exc)) from exc

        suffix = _suffix_for_format(request.format)
        filename = f"tts-{uuid.uuid4().hex}{suffix}"
        path = self.audio_dir / filename
        path.write_bytes(result.audio_bytes)
        return AudioTtsArtifact(
            path=path,
            filename=filename,
            model=result.model,
            voice=request.voice,
            duration_seconds=_duration_from_wav(result.audio_bytes)
            if request.format == "wav"
            else None,
        )

    async def stt(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        language: str = "auto",
        enhance: bool = False,
    ) -> AudioSttResponse:
        if not self.client.api_key:
            raise AudioServiceError("GEMINI_API_KEY is required for transcription.")

        try:
            result = await self.client.transcribe_audio(
                audio_bytes=file_bytes,
                mime_type=content_type,
                language=language,
                enhance=enhance,
                model=self.client.audio_model,
            )
        except GeminiError as exc:
            raise AudioServiceError(str(exc)) from exc

        return AudioSttResponse(
            text=result.text,
            raw_text=result.text,
            enhanced=enhance,
            model=result.model,
            language=language if language != "auto" else None,
        )


def _mime_type_for_format(audio_format: str) -> str:
    return {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "pcm": "audio/L16",
    }.get(audio_format, "audio/wav")


def _suffix_for_format(audio_format: str) -> str:
    return {
        "wav": ".wav",
        "mp3": ".mp3",
        "opus": ".opus",
        "aac": ".aac",
        "flac": ".flac",
        "pcm": ".pcm",
    }.get(audio_format, ".wav")


def _duration_from_wav(data: bytes) -> float | None:
    try:
        import wave

        with wave.open(io.BytesIO(data), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            if rate:
                return frames / float(rate)
    except Exception:
        return None
    return None
