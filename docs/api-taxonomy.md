# Nexus API

This document defines how Nexus concepts map to API routes.

## Route structure

Platform primitives live at `/v1/{noun}`. Capability-specific actions live at `/v1/{capability}/{action}`.

```
/health
/v1/runs
/v1/experiments
/v1/evaluations          ← not yet exposed
/v1/jobs                 ← not yet exposed
/v1/artifacts            ← not yet exposed
/v1/benchmarks           ← not yet exposed

/v1/audio/health
/v1/audio/tts
/v1/audio/transcribe

/v1/chat/completions

/openapi.json           ← generated OpenAPI schema
/docs                   ← interactive Swagger UI
/redoc                  ← alternate docs view
```

## What exists today

- `GET /health`
- `GET /v1/runs`, `GET /v1/runs/{id}`, `DELETE /v1/runs/{id}`
- `GET /v1/experiments`, `POST /v1/experiments`, `GET /v1/experiments/{experiment_id}`, `GET /v1/experiments/{experiment_id}/results`
- `GET /v1/audio/health`, `POST /v1/audio/tts`, `POST /v1/audio/transcribe`
- `POST /v1/chat/completions` (text inference)

## Rules

**Use nouns, not verbs, for resources.** `/v1/runs` not `/v1/run-history`.

**Capability routes own modality-specific payloads.** Speaker-preset and text payloads will differ. That is fine. The naming rule is about the route structure, not forcing identical shapes.

**Platform routes stay stable across capabilities.** `/v1/runs` covers inference runs, training runs, and experiment trials. It is not `/v1/inference-runs`.

**Do not encode implementation detail into routes.** `/v1/experiments` not `/v1/experiment-api`.

## Adding a new route

If it is a cross-platform resource: `/v1/{noun}`.  
If it is modality-specific: `/v1/{capability}/{action}`.  
If it is an implementation detail: do not put it in the route.
