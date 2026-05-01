set shell := ["zsh", "-cu"]

voice_compose := "infra/compose/voice-compose.yml"

default:
  @just --list

voice-up:
  docker compose -f {{voice_compose}} up --build -d

voice-down:
  docker compose -f {{voice_compose}} down

voice-logs:
  docker compose -f {{voice_compose}} logs -f voice-api

voice-api:
  cd apps/voice-api && ./run.sh

voice-kokoro:
  cd research/voice/kokoro && ./run.sh

voice-whisper:
  cd research/voice/whisper-docker-test && ./run.sh

voice-health:
  curl -sS http://127.0.0.1:8787/health

voice-tts-kokoro text="Hello from Kokoro through just.":
  curl -sS -X POST http://127.0.0.1:8787/tts/kokoro \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"{{text}}\"}" \
    --output /private/tmp/kokoro-just.wav
  ls -lh /private/tmp/kokoro-just.wav

voice-transcribe file="/private/tmp/kokoro-just.wav":
  curl -sS -X POST http://127.0.0.1:8787/transcribe \
    -F "audio=@{{file}}"
