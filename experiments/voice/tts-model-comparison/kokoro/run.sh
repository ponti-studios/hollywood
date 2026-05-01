#!/bin/sh
set -eu

docker build -t nexus-kokoro-tts .
docker run --rm \
  -v "$PWD:/work" \
  -v "$PWD/.cache:/root/.cache" \
  nexus-kokoro-tts
