from __future__ import annotations

from pathlib import Path

from hollywood.config import HollywoodSettings
from hollywood.registry import list_sources


def test_settings_resolve_data_paths(monkeypatch) -> None:
    monkeypatch.setenv("HOLLYWOOD_DATA_DIR", "custom-data")
    settings = HollywoodSettings()
    assert settings.data_dir == Path("custom-data")
    assert settings.raw_dir == Path("custom-data/raw")
    assert settings.parquet_dir == Path("custom-data/parquet")


def test_source_registry_contains_expected_groups() -> None:
    sources = {source.source_id: source for source in list_sources()}
    assert "news" in sources["variety"].groups
    assert "directories" in sources["wga"].groups
    assert sources["tmdb"].api_key_env == "TMDB_API_KEY"
