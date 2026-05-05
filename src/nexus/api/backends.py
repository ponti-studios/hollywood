from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TEXT_MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
DEFAULT_TEXT_MODEL_URL = "http://nexus-text:8080"
DEFAULT_AUDIO_TTS_URL = "http://nexus-audio-tts:8001"
DEFAULT_AUDIO_ASR_URL = "http://nexus-audio-asr:8002"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8787"


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


@dataclass(frozen=True)
class ApiBackends:
    text_model_id: str = DEFAULT_TEXT_MODEL_ID
    text_model_url: str = DEFAULT_TEXT_MODEL_URL
    audio_tts_url: str = DEFAULT_AUDIO_TTS_URL
    audio_asr_url: str = DEFAULT_AUDIO_ASR_URL

    @classmethod
    def default(cls) -> ApiBackends:
        return cls(
            text_model_id=DEFAULT_TEXT_MODEL_ID,
            text_model_url=_normalize_url(DEFAULT_TEXT_MODEL_URL),
            audio_tts_url=_normalize_url(DEFAULT_AUDIO_TTS_URL),
            audio_asr_url=_normalize_url(DEFAULT_AUDIO_ASR_URL),
        )
