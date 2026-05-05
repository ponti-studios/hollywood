# Nexus Platform Architecture

This document is the **canonical definition of Nexus**.

Nexus is the studio control plane for multimodal inference, training, and
evaluation. It is the top-level platform identity above every capability,
workflow, and runtime surface in this repo.

Use `nexus` for:

- the platform noun
- the deployable runtime
- the root service name
- the top-level developer and operator interface

Do **not** use a capability name, model name, or transport detail as the
platform identity.

Canonical supporting docs:

- taxonomy index: `docs/taxonomy/README.md`
- api contract: `docs/api-taxonomy.md`
- storage model: `docs/storage-model.md`
- canonical schemas: `src/nexus/*/schema.py`

## Platform role

Nexus owns the top-level runtime for:

- inference
- training
- evaluation
- experiments
- run history
- model management
- modality-specific capabilities like audio, text, and image

In practical terms, the deployable unit is `nexus`.

## Current platform surfaces

Today, Nexus is represented by:

- the `nexus` package
- the `nexus api serve` control-plane command
- the root `compose.yml` service named `nexus`
- the shared API surface under `/health` and `/v1/*`

## Bounded contexts

Keep platform identity and capability identity separate.

- `nexus.api` — transport and control-plane entrypoints
- `nexus.runs` — platform run records and durable execution history
- `nexus.audio` — audio generation and transcription domain
- `nexus.experiments` — benchmark execution and scoring
- `nexus.trainers` — model training workflows
- `nexus.evaluation` — evaluation metrics and judge flows
- `nexus.models` — model loading and adapter management

## Runtime topology

### Current state

The `nexus` service runs the API/control plane.

The control plane starts private backend containers for the public API to proxy:

- `infra/images/text/text.dockerfile`
- `infra/images/audio/tts.dockerfile`
- `infra/images/audio/asr.dockerfile`

This keeps the public API small while still making text, TTS, and STT easy to
test locally with `curl`.

### Implications

- local development is simple and flexible
- backend containers can be rebuilt independently of the public API
- first-request latency can include model download time
- the host machine is no longer part of the runtime contract

## Naming rules

Use these conventions consistently:

- top-level service: `nexus`
- modality/domain: `audio`, `image`, `text`, `train`, `eval`
- transport/process detail: `api`, `worker`, `runner`

Examples:

- good: `nexus` service exposing `/v1/audio/*`
- good: `audio` as a domain module under `src/nexus/audio`
- avoid: naming the whole platform service `audio-api`

## Near-term roadmap

1. Keep `nexus` as the single control-plane service.
2. Continue treating `audio` as a bounded context inside Nexus.
3. Add more bounded contexts for image and text generation.
4. Split heavyweight worker execution behind explicit adapters.
5. Decide whether training/eval stay in-process or become job workers.

## Deployment principle

Nexus should be the stable platform noun.
Capability-specific workers can evolve independently without renaming the control plane.
