from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VoicePaths:
    repo_root: Path
    data_root: Path
    images_root: Path
    research_root: Path
    kokoro_root: Path
    whisper_root: Path
    assets_root: Path
    tts_assets_root: Path
    stt_assets_root: Path
    runtime_root: Path


def default_voice_paths() -> VoicePaths:
    repo_root = Path(__file__).resolve().parents[3]
    data_root = repo_root / ".data" / "voice"
    research_root = repo_root / "research" / "voice"
    assets_root = repo_root / "assets" / "voice"

    return VoicePaths(
        repo_root=repo_root,
        data_root=data_root,
        images_root=repo_root / "infra" / "images" / "voice",
        research_root=research_root,
        kokoro_root=research_root / "kokoro",
        whisper_root=research_root / "whisper-docker-test",
        assets_root=assets_root,
        tts_assets_root=assets_root / "tts",
        stt_assets_root=assets_root / "stt",
        runtime_root=data_root / "api" / "runtime",
    )
