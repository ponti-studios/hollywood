set shell := ["zsh", "-cu"]

default:
    @just --list

# ──────────────────────────────────────────────────────────────────────────────
# Runtime
# ──────────────────────────────────────────────────────────────────────────────

start host="127.0.0.1" port="8787":
    uv run python -m uvicorn nexus.api.app:app --host {{ host }} --port {{ port }}

dev host="127.0.0.1" port="8787":
    uv run python -m uvicorn nexus.api.app:app --reload --host {{ host }} --port {{ port }}

health:
    curl -sS http://127.0.0.1:8787/health

# ──────────────────────────────────────────────────────────────────────────────
# API Helpers
# ──────────────────────────────────────────────────────────────────────────────

api-chat prompt="Hello from Nexus." model="gpt-4.1-mini":
    curl -sS -X POST http://127.0.0.1:8787/text/reply \
      -H "Content-Type: application/json" \
      -d "{\"prompt\":\"{{ prompt }}\",\"model\":\"{{ model }}\"}"

api-tts text="Hello from Nexus." speaker="alloy":
    response=$(curl -sSf -X POST http://127.0.0.1:8787/audio/tts \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"{{ text }}\",\"voice\":\"{{ speaker }}\"}")
    audio_url=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["audio_url"])' <<<"$response")
    curl -sSf "http://127.0.0.1:8787${audio_url}" --output /private/tmp/nexus-tts.wav
    ls -lh /private/tmp/nexus-tts.wav

api-stt file="/private/tmp/nexus-tts.wav":
    curl -sS -X POST http://127.0.0.1:8787/audio/stt -F "file=@{{ file }}"

# ──────────────────────────────────────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────────────────────────────────────

setup:
    uv pip install -e ".[dev]"

test:
    uv run pytest

test-cov:
    uv run pytest --cov=nexus --cov-report=term-missing

lint:
    uv run ruff check src/ tests/

format:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

typecheck:
    uv run pyright src/

clean:
    rm -rf .pytest_cache dist/ .ruff_cache/ .build/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

help:
    @just --list
