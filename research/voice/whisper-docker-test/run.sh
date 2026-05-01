#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/../../.." && pwd)"
ASSETS_DIR="$REPO_ROOT/assets/voice/stt"

mkdir -p "$ASSETS_DIR"

docker build -f "$REPO_ROOT/infra/images/voice/stt.dockerfile" -t whisper-docker-smoke "$REPO_ROOT"
docker run --rm --entrypoint sh -v "$ROOT_DIR:/work" whisper-docker-smoke /work/make-tts.sh
docker run --rm -v "$ROOT_DIR:/work" -v "$ROOT_DIR/.cache:/root/.cache/whisper" whisper-docker-smoke espeak-sample.wav --model tiny --language en --output_format txt --output_dir /work
cp "$ROOT_DIR/espeak-sample.wav" "$ASSETS_DIR/espeak-sample.wav"
cp "$ROOT_DIR/espeak-sample.txt" "$ASSETS_DIR/espeak-sample.txt"
