from __future__ import annotations

import os
from dataclasses import dataclass


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


@dataclass(frozen=True)
class ApiBackends:
    text_model_id: str
    text_model_url: str
    audio_tts_url: str
    audio_asr_url: str

    @classmethod
    def from_env(cls) -> ApiBackends:
        return cls(
            text_model_id=os.getenv(
                "NEXUS_TEXT_MODEL_ID", "HuggingFaceTB/SmolLM2-135M-Instruct"
            ),
            text_model_url=_normalize_url(
                os.getenv("NEXUS_TEXT_MODEL_URL", "http://nexus-text:8080")
            ),
            audio_tts_url=_normalize_url(
                os.getenv("NEXUS_AUDIO_TTS_URL", "http://nexus-audio-tts:8001")
            ),
            audio_asr_url=_normalize_url(
                os.getenv("NEXUS_AUDIO_ASR_URL", "http://nexus-audio-asr:8002")
            ),
        )
