from __future__ import annotations

from fastapi.testclient import TestClient

from nexus.api.app import app


def test_api_exposes_text_and_audio_routes() -> None:
    paths = {
        route.path
        for route in app.routes
        if hasattr(route, "methods") and route.path.startswith("/v1/")
    }

    assert "/v1/chat/completions" in paths
    assert "/v1/audio/health" in paths
    assert "/v1/audio/tts" in paths
    assert "/v1/audio/transcribe" in paths
    assert "/v1/experiments/{experiment_id}" in paths


def test_health_reports_audio_capability() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "audio" in payload["capabilities"]
