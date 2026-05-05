from __future__ import annotations

from nexus.audio.paths import default_audio_paths
from nexus.audio.service import AudioService


def test_default_audio_paths_resolve_repo_layout() -> None:
    paths = default_audio_paths()

    assert paths.repo_root.name == "nexus"
    assert paths.images_root == paths.repo_root / "infra" / "images" / "audio"
    assert paths.tts_assets_root == paths.repo_root / "assets" / "audio" / "tts"
    assert paths.asr_assets_root == paths.repo_root / "assets" / "audio" / "asr"
    assert paths.runtime_root == paths.repo_root / ".data" / "audio" / "api" / "runtime"


def test_audio_service_health_reports_expected_fields() -> None:
    paths = default_audio_paths()
    service = AudioService(paths=paths)

    health = service.health()

    assert health["ok"] is True
    assert "tts" in health
    assert "asr" in health
    assert health["tts"]["model"] == "Qwen3-TTS-12Hz-1.7B-CustomVoice"
    assert "supported_speakers" in health["tts"]
    assert health["asr"]["model"] == "Qwen3-ASR-1.7B"
