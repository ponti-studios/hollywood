# Nexus

## What it means

Nexus is the top-level platform identity.

It is the control plane for multimodal generative workflows, including:

- inference
- training
- evaluation
- experiments
- run tracking
- model management
- modality-specific capabilities like voice, text, and image

`nexus` is the stable platform noun. It should not be replaced by the name of a
single capability, model, or transport layer.

## How it fits in the platform

Nexus sits above every capability and workflow.

It owns:

- the primary API surface
- runtime orchestration
- cross-cutting storage and metadata
- the stable developer and operator interface
- the naming contract for platform concepts

In practical terms, the deployable service is `nexus`, not `voice`, `train`, or
`eval`.

## How it works in Nexus

Today, Nexus is represented by:

- the `nexus` package
- the `nexus api serve` control-plane command
- the root `compose.yml` service named `nexus`
- the shared API surface under `/health` and `/v1/*`

As Nexus grows, new bounded contexts should attach to the platform without
changing the platform noun.

Examples:

- good: `nexus` exposes `/v1/voice/*`
- good: `nexus` runs voice and experiment flows
- avoid: renaming the whole runtime to `voice-api`

## Design rules

- Use `nexus` for the platform, repo identity, root runtime, and top-level docs.
- Do not use a capability name as the platform name.
- Do not use a transport detail like `api` as the platform identity.
- Keep `nexus` stable even as capabilities and providers change.

## Current code fit

Relevant surfaces include:

- `src/nexus/api`
- `compose.yml`
- `infra/compose/nexus-compose.yml`
- `docs/platform-architecture.md`

## Future role

Nexus should become the stable contract between:

- creative tooling
- model runtimes
- evaluation systems
- benchmark workflows
- job orchestration
- future studio products
