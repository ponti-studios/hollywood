# Training

## What it means

Training is the workflow that updates model parameters or adapters to create a
new model state.

Examples include:

- supervised fine-tuning
- LoRA training
- DPO
- ORPO
- GRPO

Training is a model-improving workflow.

## How it fits in the platform

Training is one of the major execution domains inside Nexus.

It consumes:

- models
- datasets
- recipes or configs
- compute resources

It produces:

- new checkpoints or adapters
- training metrics
- logs
- artifacts
- run and job records

## How it works in Nexus

Today, training is represented mainly by:

- `src/nexus/trainers/*`
- `src/nexus/cli/train.py`
- recipe/config structures under `configs/recipes/*`

Longer term, Nexus should treat training as a first-class workflow with:

- explicit training runs
- job lifecycle management
- output artifact registration
- clear lineage from base model to trained result

## Design rules

- Use `training` for workflows that modify model state.
- Do not mix training semantics with evaluation semantics.
- Training should emit durable artifacts and metadata.
- Training should be configurable, reproducible, and traceable.

## Not the same as

- **Inference**: produces outputs from a model
- **Evaluation**: scores quality
- **Experiment**: compares variants and hypotheses

## Future role

Nexus should eventually elevate training from a collection of trainer modules
into a broader platform workflow with run tracking, job orchestration, artifact
registration, and lineage-aware reporting.
