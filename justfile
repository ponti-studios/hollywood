set shell := ["zsh", "-cu"]

nexus_compose := "compose.yml"
cli_build_dir := ".build/nexus-cli"

default:
    @just --list

# ──────────────────────────────────────────────────────────────────────────────
# Nexus Runtime Targets
# ──────────────────────────────────────────────────────────────────────────────

nexus-up:
    docker compose -f {{ nexus_compose }} up --build -d

nexus-down:
    docker compose -f {{ nexus_compose }} down

nexus-logs:
    docker compose -f {{ nexus_compose }} logs -f nexus nexus-text nexus-audio-tts nexus-audio-asr

nexus-health:
    curl -sS http://127.0.0.1:8787/health

api-chat prompt="Hello from Nexus." model="gpt-4.1-mini":
    curl -sS -X POST http://127.0.0.1:8787/text/reply \
      -H "Content-Type: application/json" \
      -d "{\"prompt\":\"{{ prompt }}\",\"model\":\"{{ model }}\"}"

api-tts text="Hello from Nexus." speaker="serena":
    response=$(curl -sSf -X POST http://127.0.0.1:8787/audio/tts \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"{{ text }}\",\"voice\":\"{{ speaker }}\"}")
    audio_url=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["audio_url"])' <<<"$response")
    curl -sSf "http://127.0.0.1:8787${audio_url}" --output /private/tmp/nexus-tts.wav
    ls -lh /private/tmp/nexus-tts.wav

api-stt file="/private/tmp/nexus-tts.wav":
    curl -sS -X POST http://127.0.0.1:8787/audio/stt -F "file=@{{ file }}"

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────

setup:
    uv pip install -e ".[dev]"

setup-runtime:
    uv pip install -e ".[runtime]"

setup-train:
    uv pip install -e ".[train]"

setup-notebook:
    uv pip install -e ".[notebook]"

setup-all:
    uv pip install -e ".[all]"

# Compatibility alias retained for old muscle memory.
setup-apple: setup-train
    @:

install: setup-train
    @:

install-cli: clean
    uv build --wheel
    rm -rf {{ cli_build_dir }}
    uv venv {{ cli_build_dir }}
    uv pip install --python {{ cli_build_dir }}/bin/python dist/nexus-*.whl
    mkdir -p "$HOME/.local/bin"
    install -m 0755 {{ cli_build_dir }}/bin/nexus "$HOME/.local/bin/nexus"

# ──────────────────────────────────────────────────────────────────────────────
# Training
# ──────────────────────────────────────────────────────────────────────────────

train recipe="configs/recipes/sft_lora.yaml":
    uv run nexus train --recipe "{{ recipe }}"

train-sft:
    uv run nexus train --recipe configs/recipes/sft_lora.yaml

train-dpo:
    uv run nexus train --recipe configs/recipes/dpo.yaml

train-orpo:
    uv run nexus train --recipe configs/recipes/orpo.yaml

train-grpo:
    uv run nexus train --recipe configs/recipes/grpo.yaml

# ──────────────────────────────────────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────────────────────────────────────

eval checkpoint:
    uv run nexus eval --checkpoint "{{ checkpoint }}"

# ──────────────────────────────────────────────────────────────────────────────
# Data
# ──────────────────────────────────────────────────────────────────────────────

data-alpaca:
    uv run nexus data download --name tatsu-lab/alpaca

data-ultrafeedback:
    uv run nexus data download --name trl-lib/ultrafeedback_binarized

# ──────────────────────────────────────────────────────────────────────────────
# Experiments
# ──────────────────────────────────────────────────────────────────────────────

exp-baseline:
    uv run nexus experiment run --config configs/benchmarks/exp_01.yaml

exp-baseline-quick:
    uv run nexus experiment run --samples 50 --no-wandb

exp-open-book:
    uv run nexus experiment run --config configs/benchmarks/exp_02.yaml

exp-reflection:
    uv run nexus experiment run --config configs/benchmarks/exp_03.yaml

smoke-eval model="google/gemma-4-E2B-it" samples="25":
    echo "=== Phase 1: closed-book baseline ==="
    uv run nexus experiment run --phase 1 --samples {{ samples }} \
      --large-model "{{ model }}" --no-wandb
    echo "=== Phase 2: open-book (tool use) ==="
    uv run nexus experiment run --phase 2 --samples {{ samples }} \
      --large-model "{{ model }}" --no-wandb
    echo "=== Phase 3: reflection (draft/critique/refine) ==="
    uv run nexus experiment run --phase 3 --samples {{ samples }} \
      --large-model "{{ model }}" --no-wandb
    echo "=== Smoke eval complete. Review .data/benchmarks/cache/ for outputs. ==="

# ──────────────────────────────────────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────────────────────────────────────

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
    rm -rf .pytest_cache dist/ .ruff_cache/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

help:
    @just --list
