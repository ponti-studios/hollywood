# Voice Research

This directory holds disposable and comparative voice research work.

- `kokoro/`: local TTS runner and notes.
- `whisper-docker-test/`: local Whisper smoke tests.

These paths are not application entrypoints. The runnable Nexus API lives in
[`src/nexus/api`](../../src/nexus/api) and is started via `nexus api serve` or
via the Compose service.
