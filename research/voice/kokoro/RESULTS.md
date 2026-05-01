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

## Provider Decision

- Active provider: `hexgrad/Kokoro-82M`
- Removed provider: `microsoft/VibeVoice-Realtime-0.5B`
- Reason: Kokoro is materially simpler to operate locally and is the better fit for the current Nexus voice API.
