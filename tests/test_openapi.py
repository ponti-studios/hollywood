from __future__ import annotations

from fastapi.testclient import TestClient

from nexus.api.app import app


def test_api_root_links_to_docs_and_schema() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["docs_url"] == "/docs"
    assert payload["redoc_url"] == "/redoc"
    assert payload["openapi_url"] == "/openapi.json"
    assert "text" in payload["capabilities"]
    assert "audio" in payload["capabilities"]


def test_openapi_documents_public_routes() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()

    assert spec["info"]["title"] == "Nexus API"
    assert spec["info"]["version"] == "0.1.0"
    assert {tag["name"] for tag in spec["tags"]} == {"text", "audio", "experiments", "runs"}

    paths = spec["paths"]
    assert "/health" in paths
    assert "/v1/chat/completions" in paths
    assert "/v1/audio/health" in paths
    assert "/v1/audio/tts" in paths
    assert "/v1/audio/transcribe" in paths
    assert "/v1/experiments/{experiment_id}" in paths
    assert "/v1/experiments/{experiment_id}/results" in paths
    assert "/v1/experiments" in paths
    assert "/v1/runs" in paths

    assert "audio/wav" in paths["/v1/audio/tts"]["post"]["responses"]["200"]["content"]
    assert "/v1/models" not in paths
    assert "/v1/models/load" not in paths
    assert "/v1/experiments/{run_id}" not in paths
