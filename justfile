set shell := ["zsh", "-cu"]

default:
    @just --list

setup:
    uv sync --extra dev

test:
    uv run python -m pytest tests/

smoke:
    uv run hollywood --help

integration:
    ./scripts/cli/integration/hollywood.sh

run ARGS="--help":
    uv run hollywood {{ARGS}}

lint:
    uv run ruff check src/ tests/

format:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

typecheck:
    uv run python -m pyright src/

export:
    uv run hollywood export --all

clean:
    rm -rf .pytest_cache dist/ .ruff_cache/ .build/ .venv data/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

help:
    @just --list

# ── API ──────────────────────────────────────────────────────────────────────
api-setup:
    cd api && npm install

api-dev:
    cd api && npx tsx src/index.ts

api-typecheck:
    cd api && npx tsc --noEmit

api-build:
    cd api && npx tsc

api-start:
    cd api && node dist/index.js
