from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from nexus.api.app import app
from nexus.providers.openrouter import OpenRouterTextResult


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
