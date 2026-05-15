from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_TEXT_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_STT_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_OPENAI_TTS_VOICE = "alloy"
DEFAULT_NEXUS_AUDIO_DIR = Path(".data/audio")


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    openai_api_key: str | None = None
    openai_base_url: str = DEFAULT_OPENAI_BASE_URL
    openai_text_model: str = DEFAULT_OPENAI_TEXT_MODEL
    openai_image_model: str = DEFAULT_OPENAI_IMAGE_MODEL
    openai_audio_model: str | None = None
    openai_tts_model: str | None = None
    openai_stt_model: str | None = None
    openai_speech_voice: str = DEFAULT_OPENAI_TTS_VOICE
    nexus_audio_dir: Path = Field(default=DEFAULT_NEXUS_AUDIO_DIR)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        return cls.model_validate(
            {
                "openai_api_key": env.get("OPENAI_API_KEY"),
                "openai_base_url": env.get("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
                "openai_text_model": env.get("OPENAI_TEXT_MODEL", DEFAULT_OPENAI_TEXT_MODEL),
                "openai_image_model": env.get("OPENAI_IMAGE_MODEL", DEFAULT_OPENAI_IMAGE_MODEL),
                "openai_audio_model": env.get("OPENAI_AUDIO_MODEL"),
                "openai_tts_model": env.get("OPENAI_TTS_MODEL"),
                "openai_stt_model": env.get("OPENAI_STT_MODEL"),
                "openai_speech_voice": env.get("OPENAI_SPEECH_VOICE", DEFAULT_OPENAI_TTS_VOICE),
                "nexus_audio_dir": env.get("NEXUS_AUDIO_DIR", str(DEFAULT_NEXUS_AUDIO_DIR)),
            }
        )

    @field_validator(
        "openai_api_key",
        "openai_audio_model",
        "openai_tts_model",
        "openai_stt_model",
        mode="before",
    )
    @classmethod
    def _normalize_optional_string(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Environment values must be strings.")
        normalized = value.strip()
        return normalized or None

    @field_validator(
        "openai_base_url",
        "openai_text_model",
        "openai_image_model",
        "openai_speech_voice",
        mode="before",
    )
    @classmethod
    def _normalize_required_string(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Environment values must be strings.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Environment values cannot be blank.")
        return normalized

    @field_validator("openai_base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OPENAI_BASE_URL must be a valid http(s) URL.")
        return normalized

    @field_validator("nexus_audio_dir", mode="before")
    @classmethod
    def _validate_audio_dir(cls, value: object) -> Path:
        if isinstance(value, Path):
            return value.expanduser()
        if not isinstance(value, str):
            raise ValueError("NEXUS_AUDIO_DIR must be a filesystem path string.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("NEXUS_AUDIO_DIR cannot be blank.")
        return Path(normalized).expanduser()

    @property
    def resolved_openai_tts_model(self) -> str:
        return self.openai_tts_model or self.openai_audio_model or DEFAULT_OPENAI_TTS_MODEL

    @property
    def resolved_openai_stt_model(self) -> str:
        return self.openai_stt_model or self.openai_audio_model or DEFAULT_OPENAI_STT_MODEL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
