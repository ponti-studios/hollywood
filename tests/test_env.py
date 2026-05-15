from __future__ import annotations

import pytest
from pydantic import ValidationError

from nexus.env import (
    DEFAULT_NEXUS_AUDIO_DIR,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_IMAGE_MODEL,
    DEFAULT_OPENAI_STT_MODEL,
    DEFAULT_OPENAI_TEXT_MODEL,
    DEFAULT_OPENAI_TTS_MODEL,
    DEFAULT_OPENAI_TTS_VOICE,
    Settings,
)


def test_settings_defaults():
    settings = Settings.from_env({})

    assert settings.openai_api_key is None
    assert settings.openai_base_url == DEFAULT_OPENAI_BASE_URL
    assert settings.openai_text_model == DEFAULT_OPENAI_TEXT_MODEL
    assert settings.openai_image_model == DEFAULT_OPENAI_IMAGE_MODEL
    assert settings.resolved_openai_tts_model == DEFAULT_OPENAI_TTS_MODEL
    assert settings.resolved_openai_stt_model == DEFAULT_OPENAI_STT_MODEL
    assert settings.openai_speech_voice == DEFAULT_OPENAI_TTS_VOICE
    assert settings.nexus_audio_dir == DEFAULT_NEXUS_AUDIO_DIR


def test_settings_support_legacy_audio_model_fallback():
    settings = Settings.from_env({"OPENAI_AUDIO_MODEL": "gpt-4o-audio-preview"})

    assert settings.resolved_openai_tts_model == "gpt-4o-audio-preview"
    assert settings.resolved_openai_stt_model == "gpt-4o-audio-preview"


def test_settings_reject_invalid_base_url():
    with pytest.raises(ValidationError):
        Settings.from_env({"OPENAI_BASE_URL": "ftp://example.com"})
