from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from nexus.api.app import app
from nexus.audio.service import AudioTtsArtifact
from nexus.providers.gemini import GeminiAudioResult, GeminiTextResult


async def _fake_health(self):
    return True


async def _fake_reply(self, **kwargs):
    prompt = kwargs.get("prompt") or ""
    model = kwargs.get("model") or self.text_model
    if "Lunch with Alex" in prompt:
        return GeminiTextResult(
            text='{"cleaned_text": "Lunch", "people": ["Alex"]}',
            model=model,
            prompt_tokens=2,
            completion_tokens=1,
        )
    if "Dinner (w/ Jamie)" in prompt:
        return GeminiTextResult(
            text='{"cleaned_text": "Dinner", "people": ["Jamie"]}',
            model=model,
            prompt_tokens=2,
            completion_tokens=1,
        )
    return GeminiTextResult(text="4", model=model, prompt_tokens=3, completion_tokens=1)


async def _fake_chat(self, **kwargs):
    return GeminiTextResult(
        text="support",
        model=kwargs.get("model") or self.text_model,
        prompt_tokens=4,
        completion_tokens=1,
    )


async def _fake_image(self, **kwargs):
    return GeminiTextResult(
        text="a red square",
        model=kwargs.get("model") or self.image_model,
        prompt_tokens=2,
        completion_tokens=1,
    )


async def _fake_tts(self, request):
    path = Path(self.audio_dir) / "tts-test.wav"
    path.write_bytes(b"RIFF0000WAVEfmt ")
    return AudioTtsArtifact(
        path=path,
        filename=path.name,
        model="gemini-2.5-flash",
        voice=request.voice,
        duration_seconds=1.0,
    )


async def _fake_stt(self, **kwargs):
    from nexus.audio.models import AudioSttResponse

    return AudioSttResponse(
        text="hello world",
        raw_text="hello world",
        enhanced=kwargs.get("enhance", False),
        model=self.client.audio_model,
        language="en",
    )


async def _fake_speech(self, **kwargs):
    return GeminiAudioResult(
        audio_bytes=b"RIFF0000WAVEfmt ",
        mime_type="audio/wav",
        model=kwargs.get("model") or self.audio_model,
        prompt_tokens=1,
        completion_tokens=1,
    )


def test_api_routes(monkeypatch):
    monkeypatch.setattr("nexus.providers.gemini.GeminiClient.health", _fake_health)
    monkeypatch.setattr("nexus.providers.gemini.GeminiClient.reply", _fake_reply)
    monkeypatch.setattr("nexus.providers.gemini.GeminiClient.chat", _fake_chat)
    monkeypatch.setattr("nexus.providers.gemini.GeminiClient.analyze_image", _fake_image)
    monkeypatch.setattr("nexus.providers.gemini.GeminiClient.synthesize_speech", _fake_speech)
    monkeypatch.setattr(
        "nexus.audio.service.AudioService.health",
        lambda self: {
            "ok": True,
            "providers": {"gemini": True},
            "models": {"tts": "gemini-2.5-flash", "stt": "gemini-2.5-flash"},
        },
    )
    monkeypatch.setattr("nexus.audio.service.AudioService.tts", _fake_tts)
    monkeypatch.setattr("nexus.audio.service.AudioService.stt", _fake_stt)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True
        assert health.json()["providers"]["gemini"] is True

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
        assert payload["model"] == "gemini-2.5-flash"
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
            data={"prompt": "Describe this image."},
            files={"image": ("image.png", b"fake", "image/png")},
        )
        assert image.status_code == 200
        assert image.json()["text"] == "a red square"

        tts = client.post("/audio/tts", json={"text": "Hello there"})
        assert tts.status_code == 200
        assert tts.json()["filename"].endswith(".wav")

        stt = client.post("/audio/stt", files={"file": ("clip.wav", b"fake", "audio/wav")})
        assert stt.status_code == 200
        assert stt.json()["text"] == "hello world"
