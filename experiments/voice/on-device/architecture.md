# On-Device-Only Voice Architecture

Date: 2026-05-01

## Product statement

Nexus Voice runs entirely on-device for Apple users. No cloud inference path is required for core features.

## Core requirements

1. All speech and text processing runs locally.
2. App works without network once model packs are installed.
3. Model packs can be installed, removed, and upgraded safely.
4. The runtime supports multiple inference backends behind one stable interface.

## Target platforms

- Primary: iOS and macOS.
- Runtime strategy:
  - Core ML first.
  - MLX fallback for macOS where needed.

## Runtime boundaries

- UI layer: SwiftUI app surfaces local features.
- Engine layer: `VoiceLabKit` package owns model execution.
- Storage layer: model pack registry + cache + generated artifacts.
- No remote inference lane in production mode.

## Engine modules

1. `VoiceEngine`
   - Orchestrates TTS and STT requests.
   - Selects backend by capability and policy.

2. `TranscriptionEngine`
   - Accepts local audio file URL.
   - Returns transcript text and timing metadata.

3. `SynthesisEngine`
   - Accepts text plus voice options.
   - Returns generated waveform metadata and output URL.

4. `ModelPackManager`
   - Installs and validates local model packs.
   - Tracks active/default packs.

## Data flow

1. Client sends local request to `VoiceEngine`.
2. `VoiceEngine` validates request and chooses backend.
3. Backend executes model inference locally.
4. Result is returned as typed response with local output reference.

## Backend abstraction

- `BackendType.coreml`
- `BackendType.mlx`
- `BackendType.mock` for tests and development

Backends are swappable and selected via policy, not hardcoded in feature code.

## Model pack format

Each pack should include:

- `manifest.json`
- model binaries
- tokenizer and preprocessing metadata
- voice preset metadata if TTS
- checksums

Manifest fields:

- `id`
- `version`
- `task` (`tts` or `stt`)
- `backend` (`coreml` or `mlx`)
- `locale`
- `size_bytes`
- `entrypoint`

## Security and privacy

- Default mode is local-only.
- No background upload of user audio or transcripts.
- Files should live in app sandbox storage.
- Optional export operations are explicit user actions.

## Performance strategy

- Keep small default packs for fast startup.
- Allow optional larger packs for higher quality.
- Add warmup hooks for active pack at launch.
- Cache frequent voice presets.

## Milestones

1. Engine contract + mock backend.
2. Core ML STT path.
3. Core ML TTS path.
4. Model pack install and versioning.
5. UX polish for offline pack management.

## Current scaffold status

- `VoiceLabKit` contains protocol-first runtime boundaries.
- `FileSystemModelPackManager` loads manifests from local JSON.
- `CoreMLSynthesisEngine` and `CoreMLTranscriptionEngine` are wired into the runtime and currently return explicit `INFERENCE_FAILED` until model adapters are connected.
- `VoiceLabCLI` can run health, tts, and stt flows in local mock mode and health in coreml mode.
