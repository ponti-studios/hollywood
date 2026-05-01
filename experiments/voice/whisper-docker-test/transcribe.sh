#!/bin/sh
set -eu

docker run --rm -v "$PWD:/work" -v "$PWD/.cache:/root/.cache/whisper" whisper-docker-smoke espeak-sample.wav --model tiny --language en --output_format txt --output_dir /work
