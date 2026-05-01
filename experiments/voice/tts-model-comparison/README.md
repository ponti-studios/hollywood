# TTS Model Comparison

Local experiments for lightweight text-to-speech models.

## Models

- Kokoro: `hexgrad/Kokoro-82M`
- VibeVoice Realtime: `microsoft/VibeVoice-Realtime-0.5B`

## Run Kokoro

From `~/Developer/nexus/experiments/voice`:

```sh
just kokoro
```

Or directly:

```sh
cd ~/Developer/nexus/experiments/voice/tts-model-comparison/kokoro
./run.sh
```

Outputs:

- `outputs/kokoro.wav`

## Run VibeVoice Realtime

From `~/Developer/nexus/experiments/voice`:

```sh
just vibevoice
```

Or directly:

```sh
cd ~/Developer/nexus/experiments/voice/tts-model-comparison/vibevoice
./run.sh
```

Outputs:

- `outputs/input_generated.wav`

VibeVoice is heavier than Kokoro and prefers CUDA or Apple MPS. The script uses a local `uv`
environment under `.venv` and runs with `--device mps` on Apple Silicon.

See `RESULTS.md` for the first local smoke-test results.
