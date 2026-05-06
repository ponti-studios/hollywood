from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: str | None = None


class TtsRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=2000,
        description="Text to synthesize into speech.",
    )


class AudioGenRequest(TtsRequest):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "Hello from Nexus",
                    "speaker": "serena",
                    "instruct": "Speak naturally",
                    "language": "English",
                }
            ]
        }
    )

    speaker: str = Field(default="serena", description="Named speaker preset to use.")
    instruct: str = Field(
        default="Speak naturally",
        description="Optional speech style or delivery instruction.",
    )
    language: str = Field(default="English", description="Language of the generated speech.")


class TtsHealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ok": True,
                    "model": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                    "supported_speakers": ["serena", "aiden"],
                }
            ]
        }
    )

    ok: bool
    model: str
    supported_speakers: list[str]


class AsrHealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"ok": True, "model": "google/gemma-4-E2B-it", "languages": 140}]}
    )

    ok: bool
    model: str
    languages: int


class AudioHealthData(BaseModel):
    ok: bool
    tts: TtsHealthResponse
    asr: AsrHealthResponse


class AudioHealthResponse(BaseModel):
    data: AudioHealthData
    role: Literal["audio"]


class AudioTranscriptionData(BaseModel):
    text: str


class AudioTranscriptionResponse(BaseModel):
    data: AudioTranscriptionData
