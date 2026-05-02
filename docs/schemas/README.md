# Nexus Canonical Schemas

This directory defines the canonical schema shapes for the main platform
primitives.

These are not yet strict database migrations or final wire contracts.
They are the target data contracts that should guide API design, storage design,
and future typed models.

## Included schemas

- [Run](./run.md)
- [Job](./job.md)
- [Evaluation](./evaluation.md)
- [Experiment](./experiment.md)
- [Artifact](./artifact.md)

## Why these schemas matter

Once these shapes are standardized, Nexus can share a consistent language
across:

- API responses
- storage records
- job orchestration
- benchmark workflows
- UI and reporting layers
- future analytics and operator tooling

## Design principle

Schema nouns should match taxonomy nouns.

- runs record execution
- jobs orchestrate work
- evaluations measure quality
- experiments compare variants
- artifacts persist outputs
