# Whisper Docker Test

Small local smoke test for running Whisper in Docker.

Whisper is speech-to-text. This bundle uses `espeak-ng` inside Docker to create
a sample TTS WAV, then runs Whisper against that audio.

## Files

- `Dockerfile` builds a minimal image with `espeak-ng`, `ffmpeg`, and `openai-whisper`.
- `make-tts.sh` generates `espeak-sample.wav` using `espeak-ng`.
- `transcribe.sh` runs Whisper on `espeak-sample.wav`.
- `run.sh` builds the image, generates TTS, and transcribes it.
- `espeak-sample.wav` is the generated test audio from the first run.
- `espeak-sample.txt` is the generated transcript from the first run.

## Run

```sh
./run.sh
```

Or run the steps manually:

```sh
docker build -t whisper-docker-smoke .
docker run --rm --entrypoint sh -v "$PWD:/work" whisper-docker-smoke /work/make-tts.sh
docker run --rm -v "$PWD:/work" -v "$PWD/.cache:/root/.cache/whisper" whisper-docker-smoke espeak-sample.wav --model tiny --language en --output_format txt --output_dir /work
```
