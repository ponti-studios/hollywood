# Nexus Platform Architecture

Nexus is the studio control plane for multimodal inference, training, and evaluation.

For the canonical platform noun model, see `docs/taxonomy/README.md`.
For implementation contracts, see `docs/api-taxonomy.md`, `docs/storage-taxonomy.md`, and `docs/schemas/README.md`.

## Platform role

Nexus owns the top-level runtime:

- text inference
- image inference
- audio TTS
- audio STT
- training workflows
- evaluation and benchmark workflows
- run history and experiment state

The deployable unit is `nexus`.

## Bounded contexts

Keep platform identity and capability identity separate.

- `nexus.api` — transport and control-plane entrypoints
- `nexus.voice` — audio generation and transcription domain
- `nexus.experiments` — benchmark execution and scoring
- `nexus.trainers` — model training workflows
- `nexus.evaluation` — evaluation metrics and judge flows
- `nexus.models` — model loading and adapter management

## Runtime topology

### Current state

The `nexus` service runs the API/control plane.

For voice, the control plane shells out to Docker to build and run modality-specific worker images:

- `infra/images/voice/tts.dockerfile`
- `infra/images/voice/stt.dockerfile`

This makes the API container a local orchestrator, not just an HTTP app.

### Implications

- local development is simple and flexible
- the service requires `/var/run/docker.sock`
- first-request latency can include image build time
- the host machine is part of the runtime contract

## Naming rules

Use these conventions consistently:

- top-level service: `nexus`
- modality/domain: `voice`, `image`, `text`, `train`, `eval`
- transport/process detail: `api`, `worker`, `runner`

Examples:

- good: `nexus` service exposing `/v1/voice/*`
- good: `voice` as a domain module under `src/nexus/voice`
- avoid: naming the whole platform service `voice-api`

## Near-term roadmap

1. Keep `nexus` as the single control-plane service.
2. Continue treating `voice` as a bounded context inside Nexus.
3. Add more bounded contexts for image and text generation.
4. Split heavyweight worker execution behind explicit adapters.
5. Decide whether training/eval stay in-process or become job workers.

## Deployment principle

Nexus should be the stable platform noun.
Capability-specific workers can evolve independently without renaming the control plane.
