"""Voice domain for Nexus."""

from nexus.voice.models import ApiError, KokoroRequest, TtsRequest
from nexus.voice.paths import VoicePaths, default_voice_paths
from nexus.voice.service import VoiceError, VoiceService

__all__ = [
    "ApiError",
    "KokoroRequest",
    "TtsRequest",
    "VoiceError",
    "VoicePaths",
    "VoiceService",
    "default_voice_paths",
]
