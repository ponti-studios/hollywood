# Nexus Taxonomy

This directory defines the canonical nouns used across the Nexus platform.

These docs exist to keep product language, API naming, package structure,
runtime behavior, and team communication aligned as Nexus grows into a
multimodal inference, training, and evaluation platform.

## Why this taxonomy exists

Nexus needs stable concepts that do not drift every time a new model,
workflow, modality, or deployment strategy is added.

These docs define those concepts.

When naming a package, API route, database table, job type, UI label, or
internal service, prefer the nouns defined here.

## Canonical platform nouns

- [Nexus](./nexus.md)
- [Capability](./capability.md)
- [Model](./model.md)
- [Inference](./inference.md)
- [Training](./training.md)
- [Evaluation](./evaluation.md)
- [Benchmark](./benchmark.md)
- [Experiment](./experiment.md)
- [Run](./run.md)
- [Job](./job.md)
- [Artifact](./artifact.md)

## Core relationship model

Nexus is the platform.
Capabilities define product domains.
Models are the assets the platform operates on.
Inference and training are execution workflows.
Evaluations measure quality.
Benchmarks standardize tests.
Experiments compare variants.
Runs record individual executions.
Jobs orchestrate work.
Artifacts persist outputs and results.

## Operating principle

Use these distinctions consistently:

- inference produces
- training improves
- evaluation measures
- experiments compare
- benchmarks standardize
- runs record
- jobs orchestrate
- artifacts persist

## How to use these docs

Use this directory when:

- adding a new API surface
- naming a new package or module
- designing storage for runs or jobs
- defining benchmark workflows
- introducing a new modality like image or video
- reviewing whether a feature belongs in evaluation or experiments

These docs are normative for Nexus naming.

## Implementation contracts

Once the nouns are clear, use these companion docs to turn them into platform
contracts:

- `docs/api-taxonomy.md`
- `docs/storage-model.md`
- `docs/naming.md`
- `src/nexus/*/schema.py`
