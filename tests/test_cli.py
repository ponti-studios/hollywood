from __future__ import annotations

from typer.testing import CliRunner

from hollywood.cli import app

runner = CliRunner()


def test_help_renders() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Hollywood data CLI" in result.stdout


def test_sources_list_shows_builtins() -> None:
    result = runner.invoke(app, ["sources", "list"])
    assert result.exit_code == 0
    assert "variety" in result.stdout
    assert "wga" in result.stdout
    assert "tmdb" in result.stdout
