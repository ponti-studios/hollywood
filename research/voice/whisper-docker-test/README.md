# Whisper Docker Test

Research smoke test for running Whisper in Docker.

Whisper is speech-to-text. This bundle uses `espeak-ng` inside Docker to create
a sample TTS WAV, then runs Whisper against that audio.

## Files

- `infra/images/voice/stt.dockerfile` is the canonical STT image definition for Whisper.
- `make-tts.sh` generates `espeak-sample.wav` using `espeak-ng`.
- `transcribe.sh` runs Whisper on `espeak-sample.wav`.
- `run.sh` builds the image, generates TTS, and transcribes it.
- Example input/output assets live under [`assets/voice/stt`](../../../assets/voice/stt).

## Run

From `~/Developer/nexus`:

```sh
just voice-whisper
```

Or directly:

```sh
cd ~/Developer/nexus/research/voice/whisper-docker-test
./run.sh
```

Or run the steps manually:

```sh
docker build -f ~/Developer/nexus/infra/images/voice/stt.dockerfile -t whisper-docker-smoke ~/Developer/nexus
docker run --rm --entrypoint sh -v "$PWD:/work" whisper-docker-smoke /work/make-tts.sh
docker run --rm -v "$PWD:/work" -v "$PWD/.cache:/root/.cache/whisper" whisper-docker-smoke espeak-sample.wav --model tiny --language en --output_format txt --output_dir /work
```
