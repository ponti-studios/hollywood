from __future__ import annotations

from nexus.voice.paths import default_voice_paths
from nexus.voice.service import VoiceService


def test_default_voice_paths_resolve_repo_layout() -> None:
    paths = default_voice_paths()

    assert paths.repo_root.name == "nexus"
    assert paths.images_root == paths.repo_root / "infra" / "images" / "voice"
    assert paths.kokoro_root == paths.repo_root / "research" / "voice" / "kokoro"
    assert paths.tts_assets_root == paths.repo_root / "assets" / "voice" / "tts"
    assert paths.stt_assets_root == paths.repo_root / "assets" / "voice" / "stt"
    assert paths.runtime_root == paths.repo_root / ".data" / "voice" / "api" / "runtime"


def test_voice_service_health_reports_expected_fields() -> None:
    paths = default_voice_paths()
    service = VoiceService(paths=paths)

    health = service.health()

    assert health["ok"] is True
    assert health["kokoro_image"] == "nexus-kokoro-tts"
    assert health["whisper_image"] == "whisper-docker-smoke"
