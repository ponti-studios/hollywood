"""Tests for explicit runtime environment guards."""

from __future__ import annotations

import click
import pytest
import transformers

from nexus import runtime
from nexus.api.backends import (
    DEFAULT_API_BASE_URL,
    DEFAULT_AUDIO_ASR_URL,
    DEFAULT_AUDIO_TTS_URL,
    DEFAULT_TEXT_MODEL_ID,
    DEFAULT_TEXT_MODEL_URL,
    ApiBackends,
)
from nexus.audio.app import create_app as create_audio_app
from nexus.experiments.runner import BaseRunner
from nexus.models.loader import load_model, load_tokenizer
from nexus.text.app import create_app as create_text_app


def test_supported_python_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.sys, "version_info", (3, 12, 5, "final", 0))
    runtime.ensure_supported_python()


def test_wrong_python_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.sys, "version_info", (3, 13, 0, "final", 0))
    with pytest.raises(click.exceptions.Exit):
        runtime.ensure_supported_python()


def test_non_apple_silicon_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(runtime.platform, "machine", lambda: "x86_64")
    with pytest.raises(click.exceptions.Exit):
        runtime.ensure_apple_silicon()


def test_missing_apple_runtime_dependency_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.sys, "version_info", (3, 12, 5, "final", 0))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(runtime.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        runtime.importlib.util, "find_spec", lambda name: None if name == "torch" else object()
    )

    with pytest.raises(click.exceptions.Exit):
        runtime.ensure_apple_runtime()


def test_present_apple_runtime_dependencies_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.sys, "version_info", (3, 12, 5, "final", 0))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(runtime.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(runtime.importlib.util, "find_spec", lambda name: object())

    runtime.ensure_apple_runtime()


def test_backends_use_fixed_defaults_ignoring_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_TEXT_MODEL_ID", "custom-model")
    monkeypatch.setenv("NEXUS_TEXT_MODEL_URL", "http://custom-text:9999")
    monkeypatch.setenv("NEXUS_AUDIO_TTS_URL", "http://custom-tts:9999")
    monkeypatch.setenv("NEXUS_AUDIO_ASR_URL", "http://custom-asr:9999")

    backends = ApiBackends.default()

    assert backends.text_model_id == DEFAULT_TEXT_MODEL_ID
    assert backends.text_model_url == DEFAULT_TEXT_MODEL_URL
    assert backends.audio_tts_url == DEFAULT_AUDIO_TTS_URL
    assert backends.audio_asr_url == DEFAULT_AUDIO_ASR_URL
    assert DEFAULT_API_BASE_URL == "http://127.0.0.1:8787"


def test_text_app_uses_fixed_default_model_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_TEXT_MODEL_ID", "custom-model")
    monkeypatch.setenv("NEXUS_TEXT_AUTOLOAD", "false")

    app = create_text_app(autoload=False)

    assert app.state.default_model_id == DEFAULT_TEXT_MODEL_ID
    assert app.state.autoload is False
    assert app.state.models == {}


def test_audio_app_defaults_to_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_AUDIO_ROLE", "asr")

    app = create_audio_app()

    assert app.state.audio_role == "tts"
    assert any(route.path == "/tts" for route in app.routes)
    assert not any(route.path == "/transcribe" for route in app.routes)


def test_model_loader_does_not_use_remote_code(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, dict[str, object]] = {}

    def fake_tokenizer_from_pretrained(model_id: str, **kwargs: object):
        captured["tokenizer"] = {"model_id": model_id, **kwargs}

        class Tokenizer:
            pad_token = None
            eos_token = "</s>"
            vocab_size = 10
            padding_side = "left"

        return Tokenizer()

    def fake_model_from_pretrained(model_id: str, **kwargs: object):
        captured["model"] = {"model_id": model_id, **kwargs}

        class Model:
            def parameters(self):
                return []

        return Model()

    monkeypatch.setattr("nexus.models.loader.AutoTokenizer.from_pretrained", fake_tokenizer_from_pretrained)
    monkeypatch.setattr("nexus.models.loader.AutoModelForCausalLM.from_pretrained", fake_model_from_pretrained)
    monkeypatch.setattr("nexus.models.loader.get_dtype", lambda: "bfloat16")
    monkeypatch.setattr("nexus.models.loader.get_device", lambda: "mps")

    class DummyCfg:
        model_id = "google/gemma-4-E2B-it"
        attn_implementation = "eager"

    load_tokenizer(DummyCfg())
    load_model(DummyCfg())

    assert "trust_remote_code" not in captured["tokenizer"]
    assert "trust_remote_code" not in captured["model"]


def test_text_pipeline_does_not_use_remote_code(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, dict[str, object]] = {}

    def fake_pipeline(task: str, **kwargs: object):
        captured["pipeline"] = {"task": task, **kwargs}

        class Tokenizer:
            eos_token_id = 0

        class Model:
            generation_config = None

        class Pipe:
            tokenizer = Tokenizer()
            model = Model()

        return Pipe()

    monkeypatch.setattr(transformers, "pipeline", fake_pipeline)

    class DummySpec:
        model_id = "google/gemma-4-E2B-it"
        inference_backend = "transformers"
        max_new_tokens = 8
        temperature = 0.0
        batch_size = 1

    runner = object()
    BaseRunner._build_pipeline(runner, DummySpec())  # type: ignore[arg-type]

    assert "trust_remote_code" not in captured.get("pipeline", {})
