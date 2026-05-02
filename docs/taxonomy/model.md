# Model

## What it means

A model is a model artifact that Nexus can load, serve, train, evaluate, or
compare.

A model may be:

- a hosted model ID
- a local checkpoint
- a fine-tuned adapter-backed model
- a quantized runtime variant
- a reference model used in evaluation or experiments

A model is an asset, not an action.

## How it fits in the platform

Models are the core assets that Nexus workflows operate on.

They are consumed by:

- inference
- evaluation
- benchmarks
- experiments

They are produced or transformed by:

- training
- export pipelines
- quantization pipelines

## How it works in Nexus

Nexus should treat models as first-class entities with metadata such as:

- model ID
- source provider
- local or remote location
- capability compatibility
- runtime backend
- adapter or checkpoint lineage

Current examples already appear in:

- `src/nexus/api/models.py`
- `src/nexus/api/routers/inference.py`
- `src/nexus/models/*`

## Design rules

- A model should have a stable identity.
- A model should not be confused with a run.
- Model metadata should be reusable across inference, training, and evaluation.
- Prefer explicit model IDs over ad hoc strings spread through the codebase.

## Not the same as

- **Run**: one execution record using a model
- **Artifact**: a persisted output produced by a run
- **Training**: the workflow that may create a new model state

## Future role

Nexus should evolve toward a more explicit model registry so models can be
tracked consistently across local development, benchmarks, and studio
production flows.
