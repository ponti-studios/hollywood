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
  docker compose -f {{nexus_compose}} logs -f nexus nexus-text nexus-audio-tts nexus-audio-asr

nexus-health:
  curl -sS http://127.0.0.1:8787/health

api-chat prompt="Hello from Nexus." model="HuggingFaceTB/SmolLM2-135M-Instruct":
  curl -sS -X POST http://127.0.0.1:8787/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"{{model}}\",\"messages\":[{\"role\":\"user\",\"content\":\"{{prompt}}\"}]}"

api-tts text="Hello from Nexus." speaker="serena":
  curl -sS -X POST http://127.0.0.1:8787/v1/audio/tts \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"{{text}}\",\"speaker\":\"{{speaker}}\"}" \
    --output /private/tmp/nexus-tts.wav
  ls -lh /private/tmp/nexus-tts.wav

api-stt file="/private/tmp/nexus-tts.wav":
  curl -sS -X POST http://127.0.0.1:8787/v1/audio/transcribe -F "audio=@{{file}}"
