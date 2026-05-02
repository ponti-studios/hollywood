# Experiment

## What it means

An experiment is a structured investigation with a hypothesis.

Examples include:

- compare model A vs model B
- compare prompt variant 1 vs variant 2
- compare retrieval on vs off
- compare fine-tuning settings
- compare two TTS engines on a voice benchmark

An experiment is the comparison layer.

## How it fits in the platform

Experiments organize decision-making.

They typically include:

- a question or hypothesis
- one or more variants
- one or more runs
- one or more evaluations
- a summary or conclusion

Experiments help Nexus move from raw execution to product learning.

## How it works in Nexus

Current experiment logic appears in:

- `src/nexus/experiments/*`
- experiment configs under `configs/benchmarks/*`
- `/v1/experiments` routes in the API

Over time, experiments should become explicit entities with:

- experiment ID
- hypothesis
- benchmark linkage
- run membership
- result summaries
- winner or recommendation metadata

## Design rules

- Use `experiment` for comparison and investigation.
- Do not use `experiment` as a synonym for evaluation.
- Experiments should be traceable to their runs and scores.
- The question being tested should be clear.

## Not the same as

- **Evaluation**: scoring and measurement
- **Run**: one concrete execution
- **Benchmark**: standardized test definition

## Future role

Experiments are how Nexus turns research and product intuition into disciplined
comparisons. They should become the standard structure for model, prompt,
backend, and workflow decisions across the studio platform.
