# Benchmark

## What it means

A benchmark is a standardized test definition used to evaluate systems in a
repeatable way.

Examples include:

- MMLU
- TriviaQA
- synthetic task suites
- future creative studio benchmark sets for style, fidelity, adherence, or
  naturalness

A benchmark defines what is being tested, not the conclusion about what won.

## How it fits in the platform

Benchmarks are shared evaluation scaffolding.

They give Nexus a stable way to:

- compare systems over time
- compare variants fairly
- measure regressions
- make quality gates explicit

Benchmarks are commonly consumed by evaluations and experiments.

## How it works in Nexus

Current benchmark logic appears in:

- `src/nexus/experiments/benchmarks/*`
- benchmark configs under `configs/benchmarks/*`

Over time, benchmarks should become explicit platform assets with:

- stable IDs
- dataset or prompt definitions
- expected scoring methods
- capability metadata
- versioning where needed

## Design rules

- A benchmark should be reusable.
- A benchmark should be separable from a single experiment.
- A benchmark should define tasks and scoring expectations clearly.
- Benchmark results should be attributable to specific runs and evaluations.

## Not the same as

- **Evaluation**: a scoring event or scoring layer
- **Experiment**: a structured comparison using one or more benchmarks
- **Run**: one execution through a benchmark workflow

## Future role

Benchmarks are how Nexus becomes disciplined about quality at platform scale.
They are the standard tests that let creative, engineering, and research teams
speak a shared quality language.
