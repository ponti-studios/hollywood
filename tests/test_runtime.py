"""Tests for explicit runtime environment guards."""

from __future__ import annotations

import click

import pytest

from nexus import runtime


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
    monkeypatch.setattr(runtime.importlib.util, "find_spec", lambda name: None if name == "torch" else object())

    with pytest.raises(click.exceptions.Exit):
        runtime.ensure_apple_runtime()


def test_present_apple_runtime_dependencies_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime.sys, "version_info", (3, 12, 5, "final", 0))
    monkeypatch.setattr(runtime.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(runtime.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(runtime.importlib.util, "find_spec", lambda name: object())

    runtime.ensure_apple_runtime()