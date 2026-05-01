#!/bin/sh
set -eu

docker build -t whisper-docker-smoke .
docker run --rm --entrypoint sh -v "$PWD:/work" whisper-docker-smoke /work/make-tts.sh
docker run --rm -v "$PWD:/work" -v "$PWD/.cache:/root/.cache/whisper" whisper-docker-smoke espeak-sample.wav --model tiny --language en --output_format txt --output_dir /work
