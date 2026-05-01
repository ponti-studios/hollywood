# On-Device Voice Lab

This folder defines the on-device-only direction for voice AI in Nexus.

## Goal

Build a local engine that runs speech-to-text and text-to-speech on Apple devices with no server dependency.

## Contents

- `architecture.md`: product and system architecture.
- `contracts/local-api-contract.md`: local request/response contract.
- `scaffold/VoiceLabKit`: Swift package scaffold for the local runtime.
- `model-packs/manifests.example.json`: sample model pack registry.

## Principles

- Offline first and offline capable.
- Local processing by default and by design.
- Stable interfaces so model backends can evolve without breaking app features.

## Toolchain

This scaffold targets Swift 6.3.

Check your active compiler:

```sh
swift --version
```

Expected major/minor: `6.3.x`.

## CLI scaffold

The Swift scaffold includes `VoiceLabCLI` for local smoke tests.

```sh
cd ~/Developer/nexus/experiments/voice/on-device/scaffold/VoiceLabKit
swift run VoiceLabCLI health --mode mock
swift run VoiceLabCLI tts --mode mock --text "hello"
swift run VoiceLabCLI stt --mode mock --input-audio /tmp/input.wav
swift run VoiceLabCLI stt-batch --mode mock --input-dir "/Volumes/ponti.drive/who else?"
```

Core ML mode uses the manifest-backed model manager:

```sh
swift run VoiceLabCLI health --mode coreml \
  --manifests ~/Developer/nexus/experiments/voice/on-device/model-packs/manifests.example.json
```

Batch transcription writes `.txt` files into the output directory:

```sh
swift run VoiceLabCLI stt-batch --mode coreml \
  --manifests ~/Developer/nexus/experiments/voice/on-device/model-packs/manifests.example.json \
  --input-dir "/Volumes/ponti.drive/who else?" \
  --output-dir /tmp/voicelab-transcripts
```
