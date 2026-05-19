from __future__ import annotations

from fastapi.testclient import TestClient

from nexus.api.app import app
from nexus.evaluation.demo import DemoResult
from nexus.providers.openrouter import AudioTranscriptionResult, OpenRouterTextResult


async def _fake_health(self):
    return True


async def _fake_reply(self, **kwargs):
    prompt = kwargs.get("prompt") or ""
    model = kwargs.get("model") or self.text_model
    if "Lunch with Alex" in prompt:
        return OpenRouterTextResult(
            text='{"cleaned_text": "Lunch", "people": ["Alex"]}',
            model=model,
            prompt_tokens=2,
            completion_tokens=1,
        )
    if "Dinner (w/ Jamie)" in prompt:
        return OpenRouterTextResult(
            text='{"cleaned_text": "Dinner", "people": ["Jamie"]}',
            model=model,
            prompt_tokens=2,
            completion_tokens=1,
        )
    return OpenRouterTextResult(text="4", model=model, prompt_tokens=3, completion_tokens=1)


async def _fake_chat(self, **kwargs):
    return OpenRouterTextResult(
        text="support",
        model=kwargs.get("model") or self.text_model,
        prompt_tokens=4,
        completion_tokens=1,
    )


async def _fake_image(self, **kwargs):
    return OpenRouterTextResult(
        text="a red square",
        model=kwargs.get("model") or self.image_model,
        prompt_tokens=2,
        completion_tokens=1,
    )


def test_api_routes(monkeypatch):
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.health", _fake_health)
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.reply", _fake_reply)
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.chat", _fake_chat)
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.analyze_image", _fake_image)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True
        assert health.json()["providers"]["openrouter"] is True

        reply = client.post("/text/reply", json={"prompt": "What is 2+2?"})
        assert reply.status_code == 200
        assert reply.json()["text"] == "4"

        chat = client.post(
            "/text/chat",
            json={"messages": [{"role": "user", "content": "What kind of request is this?"}]},
        )
        assert chat.status_code == 200
        assert chat.json()["message"]["content"] == "support"

        batch = client.post(
            "/text/analyze", json={"texts": ["Lunch with Alex", "Dinner (w/ Jamie)"]}
        )
        assert batch.status_code == 200
        payload = batch.json()
        assert payload["model"] == "anthropic/claude-sonnet-4.6"
        assert payload["provider"] == "openrouter"
        assert payload["results"][0]["cleaned_text"] == "Lunch"
        assert payload["results"][0]["people"] == ["Alex"]
        assert payload["results"][1]["cleaned_text"] == "Dinner"
        assert payload["results"][1]["people"] == ["Jamie"]

        empty_batch = client.post("/text/analyze", json={"texts": []})
        assert empty_batch.status_code == 422

        malformed_batch = client.post("/text/analyze", json={"texts": [""]})
        assert malformed_batch.status_code == 422

        image = client.post(
            "/image/analyze",
            files={"image": ("image.png", b"fake", "image/png")},
        )
        assert image.status_code == 200
        assert image.json()["text"] == "a red square"
        assert image.json()["provider"] == "openrouter"


def test_evals_route(monkeypatch):
    _fake_demo_results = [
        DemoResult(
            name="email_extraction",
            score=1.0,
            passed=True,
            response="ada@example.com",
            details="matched expected value 'ada@example.com'",
        ),
        DemoResult(
            name="classification",
            score=1.0,
            passed=True,
            response="support",
            details="matched label 'support'",
        ),
        DemoResult(
            name="json_format",
            score=0.0,
            passed=False,
            response="not json",
            details="response is not valid JSON",
        ),
    ]

    async def _fake_run_demo_evals(model=None):
        return _fake_demo_results

    monkeypatch.setattr("nexus.api.app.run_demo_evals", _fake_run_demo_evals)
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.health", _fake_health)

    with TestClient(app) as client:
        response = client.post("/evals/run")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 3
        assert payload["passed"] == 2
        assert payload["results"][0]["name"] == "email_extraction"
        assert payload["results"][0]["passed"] is True
        assert payload["results"][2]["passed"] is False


async def _fake_tts(self, **kwargs):
    return b"fake-audio-bytes"


async def _fake_stt(self, **kwargs):
    return AudioTranscriptionResult(
        text="hello from nexus",
        model=kwargs.get("model") or self.stt_model,
        seconds=1.2,
        total_tokens=10,
        cost=0.0001,
    )


def test_audio_routes(monkeypatch):
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.health", _fake_health)
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.tts", _fake_tts)
    monkeypatch.setattr("nexus.providers.openrouter.OpenRouterClient.stt", _fake_stt)

    with TestClient(app) as client:
        # TTS — returns raw audio bytes with correct content-type
        tts = client.post(
            "/audio/speech",
            json={"text": "Hello from Nexus.", "voice": "alloy"},
        )
        assert tts.status_code == 200
        assert tts.headers["content-type"] == "audio/mpeg"
        assert tts.content == b"fake-audio-bytes"

        # TTS — empty text is rejected
        bad_tts = client.post("/audio/speech", json={"text": "", "voice": "alloy"})
        assert bad_tts.status_code == 422

        # STT — returns transcription JSON
        stt = client.post(
            "/audio/transcribe",
            files={"audio": ("speech.mp3", b"fake-audio", "audio/mpeg")},
        )
        assert stt.status_code == 200
        payload = stt.json()
        assert payload["text"] == "hello from nexus"
        assert payload["provider"] == "openrouter"
        assert payload["usage"]["seconds"] == 1.2

        # Health now advertises audio capability and tts/stt models
        health = client.get("/health")
        assert health.status_code == 200
        h = health.json()
        assert "audio" in h["capabilities"]
        assert "tts" in h["models"]
        assert "stt" in h["models"]
