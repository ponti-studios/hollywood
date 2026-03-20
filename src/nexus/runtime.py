"""
runtime.py — Explicit environment guards for Apple Silicon training workflows.

The project can be installed in a lightweight development mode without the full
Apple runtime stack. Commands that actually need that stack should fail with a
clear explanation instead of a late ImportError or a cryptic wheel-resolution
problem.
"""

from __future__ import annotations

import importlib.util
import platform
import sys

import typer
from rich.console import Console

SUPPORTED_PYTHON = (3, 12)
APPLE_RUNTIME_PACKAGES = ("torch", "accelerate", "peft", "trl")
MLX_RUNTIME_PACKAGES = ("mlx", "mlx_lm")


def _package_missing(name: str) -> bool:
    return importlib.util.find_spec(name) is None


def _missing_packages(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if _package_missing(name)]


def _fail(console: Console | None, message: str) -> None:
    target = console or Console()
    target.print(f"[red]{message}[/red]")
    raise typer.Exit(code=1)


def ensure_supported_python(console: Console | None = None) -> None:
    """Require the exact Python minor version pinned in mise.toml."""
    major, minor = sys.version_info[:2]
    if (major, minor) != SUPPORTED_PYTHON:
        _fail(
            console,
            "Unsupported Python version. Use mise to install Python 3.12.x "
            "and recreate .venv before running Apple runtime commands.",
        )


def ensure_apple_silicon(console: Console | None = None) -> None:
    """Require macOS on Apple Silicon for Apple runtime commands."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        _fail(
            console,
            "This command requires macOS on Apple Silicon. "
            "Use the lightweight dev install for non-Apple environments.",
        )


def ensure_apple_runtime(console: Console | None = None) -> None:
    """Require the Apple runtime dependencies used by training/perplexity paths."""
    ensure_supported_python(console)
    ensure_apple_silicon(console)

    missing = _missing_packages(APPLE_RUNTIME_PACKAGES)
    if missing:
        joined = ", ".join(missing)
        _fail(
            console,
            "Missing Apple runtime dependencies: "
            f"{joined}. Install them with: uv pip install -e '.[dev,notebook,apple]'",
        )


def ensure_mlx_runtime(console: Console | None = None) -> None:
    """Require the MLX runtime dependencies used by serving/judge paths."""
    ensure_supported_python(console)
    ensure_apple_silicon(console)

    missing = _missing_packages(MLX_RUNTIME_PACKAGES)
    if missing:
        joined = ", ".join(missing)
        _fail(
            console,
            "Missing MLX runtime dependencies: "
            f"{joined}. Install them with: uv pip install -e '.[dev,notebook,apple]'",
        )