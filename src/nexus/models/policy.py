from __future__ import annotations

import os

DEFAULT_TEXT_MODEL_ID = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")


def get_text_model_id() -> str:
    return os.getenv("GEMINI_TEXT_MODEL", DEFAULT_TEXT_MODEL_ID)
