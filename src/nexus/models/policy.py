from __future__ import annotations

import os

DEFAULT_TEXT_MODEL_ID = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")


def get_text_model_id() -> str:
    return os.getenv("OPENAI_TEXT_MODEL", DEFAULT_TEXT_MODEL_ID)
