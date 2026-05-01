#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/../../../.." && pwd)"
ASSETS_DIR="$REPO_ROOT/assets/voice/tts"

mkdir -p "$ASSETS_DIR"

docker build -f "$REPO_ROOT/infra/images/voice/tts.dockerfile" -t nexus-kokoro-tts "$REPO_ROOT"
docker run --rm \
  -v "$ROOT_DIR:/work" \
  -v "$ROOT_DIR/.cache:/root/.cache" \
  nexus-kokoro-tts

if [ -f "$ROOT_DIR/outputs/kokoro.wav" ]; then
  cp "$ROOT_DIR/outputs/kokoro.wav" "$ASSETS_DIR/kokoro.wav"
fi
