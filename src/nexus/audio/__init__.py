"""Audio domain for Nexus - TTS and ASR services."""

from nexus.audio.models import ApiError, AudioGenRequest, TtsRequest
from nexus.audio.paths import AudioPaths, default_audio_paths
from nexus.audio.service import ASRService, AudioError, AudioService

__all__ = [
    "ApiError",
    "AudioGenRequest",
    "AudioPaths",
    "AudioService",
    "ASRService",
    "AudioError",
    "TtsRequest",
    "default_audio_paths",
]