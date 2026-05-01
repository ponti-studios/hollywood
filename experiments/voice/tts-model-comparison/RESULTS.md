# TTS Model Comparison Results

Date: 2026-04-30

## Kokoro

- Model: `hexgrad/Kokoro-82M`
- Runtime: Docker, CPU
- Output: `kokoro/outputs/kokoro.wav`
- Audio: 8.25 seconds, 24 kHz mono WAV
- Whisper tiny sanity transcript:

```text
This is Cacorro, an 82-million-parameter open-weight text to speech model running inside a local Docker experiment.
```

Notes: Generated successfully. The Docker build is large because the Linux ARM PyTorch dependency stack pulls CUDA-related wheels, but the model itself is lightweight.

## VibeVoice Realtime

- Model: `microsoft/VibeVoice-Realtime-0.5B`
- Runtime: local uv virtualenv, Apple MPS
- Output: `vibevoice/outputs/input_generated.wav`
- Audio: 5.60 seconds, 24 kHz mono WAV
- Generation time: 19.87 seconds
- Real-time factor: 3.55x
- Whisper tiny sanity transcript:

```text
This is Microsoft 5-voice real-time, a lightweight text-to-speech model for streaming voice experiments.
```

Notes: Generated successfully after pinning uv to an arm64 Python. Using Python 3.12 without architecture pinning selected an x86_64 interpreter and caused `numba` to fail compiling.

