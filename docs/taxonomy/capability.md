# Capability

## What it means

A capability is a product-facing domain inside Nexus.

Capabilities describe what kind of creative or generative work the platform can
do, such as:

- voice
- text
- image
- video
- music
- agents

A capability is not the same thing as the whole platform.
It is a bounded context within Nexus.

## How it fits in the platform

Capabilities partition the platform into clear domains.

Each capability should own:

- domain-specific requests and responses
- capability-specific adapters and workflows
- modality-specific assets and storage conventions
- routes that are specific to that capability

The platform stays named `nexus`; capabilities live under it.

## How it works in Nexus

A capability should usually map to:

- a package such as `src/nexus/voice`
- API routes such as `/v1/voice/*`
- runtime assets under capability-specific paths
- capability-specific tests, docs, and workers

Current example:

- `voice` is a capability implemented in `src/nexus/voice`

Future examples:

- `text` for text generation and chat workflows
- `image` for image generation and editing workflows

## Design rules

- Capabilities are nouns, not verbs.
- A capability owns domain logic, not the platform identity.
- Capability names should be stable and modality-oriented.
- Use capability names for bounded contexts, not for cross-platform systems.

## Not the same as

- **Nexus**: the platform
- **Inference**: the act of generating outputs
- **Model**: the asset used by the capability

## Future role

Capabilities are how Nexus scales into a true studio platform.
They allow the control plane to stay unified while domain logic remains clear
and independently evolvable.
