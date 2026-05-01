#!/bin/sh
set -eu

espeak-ng -w /work/espeak-sample.wav "Hello from the Whisper Docker smoke test. If this works, the container will transcribe this sentence."
