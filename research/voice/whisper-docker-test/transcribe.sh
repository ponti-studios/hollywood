#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
docker run --rm -v "$ROOT_DIR:/work" -v "$ROOT_DIR/.cache:/root/.cache/whisper" whisper-docker-smoke espeak-sample.wav --model tiny --language en --output_format txt --output_dir /work
