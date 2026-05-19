from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, ConfigDict, field_validator

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_TEXT_MODEL = "anthropic/claude-sonnet-4.6"
DEFAULT_OPENROUTER_IMAGE_MODEL = "anthropic/claude-sonnet-4.6"
DEFAULT_OPENROUTER_TTS_MODEL = "openai/gpt-4o-mini-tts-2025-12-15"
DEFAULT_OPENROUTER_STT_MODEL = "openai/whisper-1"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    openrouter_api_key: str | None = None
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL
    openrouter_text_model: str = DEFAULT_OPENROUTER_TEXT_MODEL
    openrouter_image_model: str = DEFAULT_OPENROUTER_IMAGE_MODEL
    openrouter_tts_model: str = DEFAULT_OPENROUTER_TTS_MODEL
    openrouter_stt_model: str = DEFAULT_OPENROUTER_STT_MODEL

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        return cls.model_validate({
            "openrouter_api_key": env.get("OPENROUTER_API_KEY"),
            "openrouter_base_url": env.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
            "openrouter_text_model": env.get(
                "OPENROUTER_TEXT_MODEL", DEFAULT_OPENROUTER_TEXT_MODEL
            ),
            "openrouter_image_model": env.get(
                "OPENROUTER_IMAGE_MODEL", DEFAULT_OPENROUTER_IMAGE_MODEL
            ),
            "openrouter_tts_model": env.get("OPENROUTER_TTS_MODEL", DEFAULT_OPENROUTER_TTS_MODEL),
            "openrouter_stt_model": env.get("OPENROUTER_STT_MODEL", DEFAULT_OPENROUTER_STT_MODEL),
        })

    @field_validator(
        "openrouter_api_key",
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
        "openrouter_base_url",
        "openrouter_text_model",
        "openrouter_image_model",
        "openrouter_tts_model",
        "openrouter_stt_model",
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

    @field_validator("openrouter_base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Environment base URLs must be valid http(s) URLs.")
        return normalized


def _load_env_file() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path, override=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_file()
    return Settings.from_env()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    _load_env_file()
    return get_settings()
