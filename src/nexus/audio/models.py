from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AudioGenRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "Hello from Nexus",
                    "voice": "Kore",
                    "format": "wav",
                }
            ]
        }
    )

    text: str = Field(min_length=1, max_length=8000, description="Text to synthesize.")
    model: str | None = Field(default=None, description="Optional TTS model override.")
    voice: str = Field(default="Kore", description="Voice preset to use.")
    format: str = Field(default="wav", description="Requested audio output format.")


class AudioTtsResponse(BaseModel):
    audio_url: str
    filename: str
    model: str
    voice: str
    duration_seconds: float | None = None


class AudioSttResponse(BaseModel):
    text: str
    raw_text: str | None = None
    enhanced: bool = False
    model: str
    language: str | None = None


class AudioHealthResponse(BaseModel):
    ok: bool
    service: str = "audio"
    providers: dict[str, bool]
    models: dict[str, str]
