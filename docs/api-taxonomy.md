# Nexus API Taxonomy

This document defines how Nexus concepts should appear at the API boundary.

It turns the platform taxonomy into concrete route naming rules so the HTTP
surface stays coherent as Nexus grows into a multimodal studio platform.

## Design goal

The API should expose:

- platform primitives as top-level nouns
- capability-specific behavior under capability prefixes
- transport-stable routes that survive backend and provider changes

The route tree should describe what Nexus is, not how a given implementation
happens to work internally.

## Route categories

### 1. Platform routes

These are cross-capability platform primitives.

Examples:

- `/health`
- `/v1/models`
- `/v1/runs`
- `/v1/jobs`
- `/v1/evaluations`
- `/v1/experiments`
- `/v1/benchmarks`
- `/v1/artifacts`

These routes should remain stable even as new capabilities are added.

### 2. Capability routes

These expose domain-specific functionality.

Examples:

- `/v1/voice/*`
- `/v1/text/*`
- `/v1/image/*`

Capability routes should be used when the payloads, semantics, or artifacts are
specific to a modality or product domain.

### 3. Operator or admin routes

These are optional later surfaces for platform operations.

Examples:

- `/v1/jobs/*`
- `/v1/workers/*`
- `/v1/providers/*`

These should not replace the core product-facing nouns.

## Current route map

Current code already exposes several correct platform nouns:

- `/health`
- `/v1/models`
- `/v1/runs`
- `/v1/experiments`
- `/v1/voice/*`

Current references:

- `src/nexus/api/app.py`
- `src/nexus/api/routers/inference.py`
- `src/nexus/api/routers/runs.py`
- `src/nexus/api/routers/experiments.py`
- `src/nexus/api/routers/voice.py`

## Target route map

### Platform

- `GET /health`
- `GET /v1/models`
- `POST /v1/models/load`
- `DELETE /v1/models/{model_id}`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/evaluations`
- `GET /v1/evaluations/{evaluation_id}`
- `GET /v1/experiments`
- `GET /v1/experiments/{experiment_id}`
- `GET /v1/benchmarks`
- `GET /v1/benchmarks/{benchmark_id}`
- `GET /v1/artifacts`
- `GET /v1/artifacts/{artifact_id}`

### Capability

#### Voice

- `GET /v1/voice/health`
- `POST /v1/voice/tts`
- `POST /v1/voice/transcribe`

#### Text

Potential future routes:

- `POST /v1/text/chat/completions`
- `POST /v1/text/embeddings`
- `POST /v1/text/moderations`

#### Image

Potential future routes:

- `POST /v1/image/generate`
- `POST /v1/image/edit`
- `POST /v1/image/variations`

## Naming rules

### Use nouns for resources

Good:

- `/v1/runs`
- `/v1/experiments`
- `/v1/artifacts`

Avoid:

- `/v1/run-history`
- `/v1/experiment-results-store`

### Use capability prefixes only for capability-specific actions

Good:

- `/v1/voice/tts`
- `/v1/voice/transcribe`

Avoid:

- `/v1/voice/runs`

Run history is a platform concern, not a voice-only concern.

### Keep transport detail out of resource identity

Good:

- `/v1/experiments`

Avoid:

- `/v1/experiment-api`

### Do not collapse evaluation into experiments

Evaluations and experiments should have different resources because they answer
different questions:

- evaluations measure
- experiments compare

## Response model guidance

### Platform primitives should have explicit typed responses

Prefer typed models for:

- runs
- experiments
- evaluations
- artifacts
- jobs

Avoid returning raw `dict` payloads once the resource stabilizes.

### Capability routes can use specialized payloads

Voice payloads will differ from image payloads. That is expected.
The taxonomy rule is about route naming, not forcing identical payload shapes.

## Current-to-target alignment

### Good current alignment

- `runs` is already a top-level resource
- `experiments` is already a top-level resource
- `voice` is correctly a capability route

### Missing or incomplete platform surfaces

- `jobs`
- `evaluations`
- `benchmarks`
- `artifacts`

These should become explicit API resources as the platform matures.

## Decision rule

When adding a new endpoint, ask:

1. Is this a cross-platform resource? Use a platform noun.
2. Is this modality-specific? Use a capability prefix.
3. Is this just implementation detail? Do not encode it into the route.

## Canonical summary

- platform nouns live at `/v1/*`
- capability nouns live at `/v1/{capability}/*`
- transport and implementation terms should not define resource identity
