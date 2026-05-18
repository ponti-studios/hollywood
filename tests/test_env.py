from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from nexus.env import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_IMAGE_MODEL,
    DEFAULT_OPENROUTER_TEXT_MODEL,
    Settings,
    reload_settings,
)


def test_settings_defaults():
    settings = Settings.from_env({})

    assert settings.openrouter_api_key is None
    assert settings.openrouter_base_url == DEFAULT_OPENROUTER_BASE_URL
    assert settings.openrouter_text_model == DEFAULT_OPENROUTER_TEXT_MODEL
    assert settings.openrouter_image_model == DEFAULT_OPENROUTER_IMAGE_MODEL


def test_settings_reject_invalid_base_url():
    with pytest.raises(ValidationError):
        Settings.from_env({"OPENROUTER_BASE_URL": "ftp://example.com"})


def test_reload_settings_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path(tmp_path / ".env").write_text(
        "OPENROUTER_API_KEY=from-file\nOPENROUTER_TEXT_MODEL=anthropic/claude-3.5-sonnet\n"
    )

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_TEXT_MODEL", raising=False)

    settings = reload_settings()

    assert settings.openrouter_api_key == "from-file"
    assert settings.openrouter_text_model == "anthropic/claude-3.5-sonnet"
