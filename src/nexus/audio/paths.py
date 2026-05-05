from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioPaths:
    repo_root: Path
    data_root: Path
    images_root: Path
    research_root: Path
    assets_root: Path
    tts_assets_root: Path
    asr_assets_root: Path
    runtime_root: Path


def default_audio_paths() -> AudioPaths:
    repo_root = Path(__file__).resolve().parents[3]
    data_root = repo_root / ".data" / "audio"
    research_root = repo_root / "research" / "audio"
    assets_root = repo_root / "assets" / "audio"

    return AudioPaths(
        repo_root=repo_root,
        data_root=data_root,
        images_root=repo_root / "infra" / "images" / "audio",
        research_root=research_root,
        assets_root=assets_root,
        tts_assets_root=assets_root / "tts",
        asr_assets_root=assets_root / "asr",
        runtime_root=data_root / "api" / "runtime",
    )
