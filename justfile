set shell := ["zsh", "-cu"]

nexus_compose := "compose.yml"

default:
  @just --list

# ──────────────────────────────────────────────────────────────────────────────
# Nexus Runtime Targets
# ──────────────────────────────────────────────────────────────────────────────

nexus-up:
  docker compose -f {{nexus_compose}} up --build -d

nexus-down:
  docker compose -f {{nexus_compose}} down

nexus-logs:
  docker compose -f {{nexus_compose}} logs -f nexus

nexus-api:
  uv run nexus api serve --host 0.0.0.0 --port 8787

voice-kokoro:
  cd research/voice/kokoro && ./run.sh

voice-whisper:
  cd research/voice/whisper-docker-test && ./run.sh

nexus-health:
  curl -sS http://127.0.0.1:8787/health

voice-tts-kokoro text="Hello from Kokoro through just.":
  curl -sS -X POST http://127.0.0.1:8787/tts/kokoro \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"{{text}}\"}" \
    --output /private/tmp/kokoro-just.wav
  ls -lh /private/tmp/kokoro-just.wav

voice-transcribe file="/private/tmp/kokoro-just.wav":
  curl -sS -X POST http://127.0.0.1:8787/transcribe -F "audio=@{{file}}"

# ──────────────────────────────────────────────────────────────────────────────
# Inference Testing
# ──────────────────────────────────────────────────────────────────────────────

test-inference:
  #!/bin/zsh
  ./scripts/run_inference_tests.sh

test-inference-quick:
  #!/bin/zsh
  ./scripts/run_inference_tests.sh --quick

test-inference-verbose:
  #!/bin/zsh
  ./scripts/run_inference_tests.sh --verbose

test-inference-model model="mlx-community/gemma-4-e2b-bf16":
  #!/bin/zsh
  ./scripts/run_inference_tests.sh --model {{model}}

analyze-inference db=".data/api/inference.db" limit="50":
  #!/bin/zsh
  python scripts/analyze_inference_runs.py --db {{db}} --limit {{limit}}
