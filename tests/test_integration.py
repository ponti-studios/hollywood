"""Live integration tests — requires the Nexus server to be running on :8787.

Run with:
    just integration-test
or:
    uv run pytest tests/test_integration.py -v
"""

from __future__ import annotations

import struct
import zlib

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8787"


def _tiny_png() -> bytes:
    """Return a minimal valid 1×1 red PNG with no external dependencies."""

    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    # filter byte 0x00 + 3-byte RGB red pixel
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health(client: httpx.Client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "nexus"
    assert set(body["capabilities"]) == {"text", "image", "evals"}
    assert "openrouter" in body["providers"]
    assert body["providers"]["openrouter"] is True
    assert "text" in body["models"]
    assert "image" in body["models"]


# ---------------------------------------------------------------------------
# POST /text/reply
# ---------------------------------------------------------------------------


def test_text_reply_happy_path(client: httpx.Client) -> None:
    r = client.post(
        "/text/reply",
        json={"prompt": "Reply with only the word: pong", "max_tokens": 16, "temperature": 0.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["text"], str)
    assert len(body["text"]) > 0
    assert body["provider"] == "openrouter"
    assert isinstance(body["model"], str)


def test_text_reply_empty_prompt_is_422(client: httpx.Client) -> None:
    r = client.post("/text/reply", json={"prompt": ""})
    assert r.status_code == 422


def test_text_reply_missing_prompt_is_422(client: httpx.Client) -> None:
    r = client.post("/text/reply", json={"max_tokens": 32})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /text/chat
# ---------------------------------------------------------------------------


def test_text_chat_happy_path(client: httpx.Client) -> None:
    r = client.post(
        "/text/chat",
        json={
            "messages": [{"role": "user", "content": "Reply with only the number 42."}],
            "max_tokens": 16,
            "temperature": 0.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["message"]["role"] == "assistant"
    assert isinstance(body["message"]["content"], str)
    assert len(body["message"]["content"]) > 0
    assert body["provider"] == "openrouter"


def test_text_chat_empty_messages_is_422(client: httpx.Client) -> None:
    r = client.post("/text/chat", json={"messages": []})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /text/analyze
# ---------------------------------------------------------------------------


def test_text_analyze_happy_path(client: httpx.Client) -> None:
    r = client.post(
        "/text/analyze",
        json={"texts": ["Lunch with Alice", "Project sync with Bob and Carol"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "openrouter"
    assert len(body["results"]) == 2
    for item in body["results"]:
        assert isinstance(item["cleaned_text"], str)
        assert isinstance(item["people"], list)
    # Alice should appear in first result
    assert "Alice" in body["results"][0]["people"]


def test_text_analyze_empty_array_is_422(client: httpx.Client) -> None:
    r = client.post("/text/analyze", json={"texts": []})
    assert r.status_code == 422


def test_text_analyze_blank_item_is_422(client: httpx.Client) -> None:
    r = client.post("/text/analyze", json={"texts": [""]})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /image/analyze
# ---------------------------------------------------------------------------


def test_image_analyze_happy_path(client: httpx.Client) -> None:
    r = client.post(
        "/image/analyze",
        files={"image": ("red.png", _tiny_png(), "image/png")},
        data={"prompt": "What color is this image? Reply with one word."},
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["text"], str)
    assert len(body["text"]) > 0
    assert body["provider"] == "openrouter"


# ---------------------------------------------------------------------------
# POST /evals/run
# ---------------------------------------------------------------------------


def test_evals_run(client: httpx.Client) -> None:
    r = client.post("/evals/run", timeout=120.0)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert isinstance(body["passed"], int)
    assert 0 <= body["passed"] <= body["total"]
    assert len(body["results"]) == 3
    names = {item["name"] for item in body["results"]}
    assert names == {"email_extraction", "classification", "json_format"}
    for item in body["results"]:
        assert isinstance(item["score"], float)
        assert isinstance(item["passed"], bool)
        assert isinstance(item["response"], str)
        assert isinstance(item["details"], str)
