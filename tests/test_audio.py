from __future__ import annotations

import asyncio
import io
from pathlib import Path

import numpy as np

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
    assert health["tts"]["model"] == "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    assert "supported_speakers" in health["tts"]
    assert health["asr"]["model"] == "google/gemma-4-E2B-it"


def test_audio_service_transcribe_uses_gemma_audio_model(monkeypatch) -> None:
    from nexus.audio import service as audio_service

    class FakeSoundFile:
        def read(self, buffer, dtype="float32"):
            return np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32), 16000

        def write(self, path, data, sr):
            Path(path).write_bytes(b"wav")

    class FakeBatch(dict):
        def to(self, device):
            return self

    captured: dict[str, object] = {}

    class FakeProcessor:
        class Tokenizer:
            eos_token_id = 0

        tokenizer = Tokenizer()

        def apply_chat_template(self, messages, **kwargs):
            captured["messages"] = messages
            return FakeBatch({"input_ids": __import__("torch").tensor([[1, 2, 3]])})

        def decode(self, tokens, skip_special_tokens=True):
            captured["decoded_tokens"] = tokens
            return "Gemma transcription"

        def parse_response(self, response):
            captured["response"] = response
            return response

    class FakeModel:
        device = "cpu"

        def eval(self):
            return self

        def generate(self, **kwargs):
            captured["generate_kwargs"] = kwargs
            return __import__("torch").tensor([[1, 2, 3, 4]])

    monkeypatch.setattr(audio_service, "_require_soundfile", lambda: FakeSoundFile())
    monkeypatch.setattr(
        audio_service,
        "_get_gemma_audio_model",
        lambda: audio_service.GemmaAudioModel(
            model_id="google/gemma-4-E2B-it",
            processor=FakeProcessor(),
            model=FakeModel(),
        ),
    )

    service = AudioService(paths=default_audio_paths())
    result = asyncio.run(service.transcribe("sample.wav", io.BytesIO(b"fake-audio")))

    assert result == "Gemma transcription"
    assert captured["messages"][0]["content"][0]["audio"].endswith(".wav")
    assert captured["messages"][0]["content"][1]["text"].startswith("Transcribe the following speech segment")
    assert captured["generate_kwargs"]["max_new_tokens"] == 256
