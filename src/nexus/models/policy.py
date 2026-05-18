from __future__ import annotations

from nexus.env import get_settings


def get_text_model_id() -> str:
    return get_settings().openrouter_text_model
