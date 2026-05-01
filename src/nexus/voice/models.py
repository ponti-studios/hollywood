from __future__ import annotations

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: str | None = None


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class KokoroRequest(TtsRequest):
    voice: str = Field(default="af_heart", min_length=1, max_length=80)
    lang_code: str = Field(default="a", min_length=1, max_length=8)
