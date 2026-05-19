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

api-chat prompt="Hello from Nexus." model="anthropic/claude-sonnet-4.6":
    curl -sS -X POST http://127.0.0.1:8787/text/reply \
      -H "Content-Type: application/json" \
      -d "{\"prompt\":\"{{ prompt }}\",\"model\":\"{{ model }}\"}"

api-analyze texts='["Lunch with Alice", "Call with Bob"]':
    curl -sS -X POST http://127.0.0.1:8787/text/analyze \
      -H "Content-Type: application/json" \
      -d "{\"texts\":{{ texts }}}"

api-evals:
    curl -sS -X POST http://127.0.0.1:8787/evals/run | python -m json.tool

api-tts text="Hello from Nexus." voice="alloy" outfile="/tmp/nexus-tts.mp3":
    curl -sS -X POST http://127.0.0.1:8787/audio/speech \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"{{ text }}\",\"voice\":\"{{ voice }}\"}" \
      --output {{ outfile }}
    ls -lh {{ outfile }}

api-stt file="/tmp/nexus-tts.mp3":
    curl -sS -X POST http://127.0.0.1:8787/audio/transcribe \
      -F "audio=@{{ file }}" | python -m json.tool

# ──────────────────────────────────────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────────────────────────────────────

setup:
    uv pip install -e ".[dev]"

test:
    uv run pytest tests/ --ignore=tests/test_integration.py

test-cov:
    uv run pytest tests/ --ignore=tests/test_integration.py --cov=nexus --cov-report=term-missing

integration-test:
    uv run pytest tests/test_integration.py -v

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
