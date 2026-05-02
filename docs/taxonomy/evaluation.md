# Evaluation

## What it means

Evaluation is the measurement layer.

It answers questions like:

- how good was the output?
- how accurate was the model?
- how natural was the audio?
- how strong was the response under a rubric?

Evaluation can be metric-based, judge-based, rubric-based, or human-in-the-loop.

## How it fits in the platform

Evaluation sits downstream of inference and training.

It consumes:

- outputs
- reference data
- benchmarks
- scorers or judges

It produces:

- scores
- judgments
- summaries
- evaluation artifacts

Experiments depend on evaluation, but evaluation is not the same thing as an
experiment.

## How it works in Nexus

Current evaluation-related logic exists in:

- `src/nexus/evaluation/*`
- parts of `src/nexus/experiments/*`

Nexus should grow toward explicit evaluation entities with:

- evaluation subjects
- scorer identity
- benchmark linkage
- metric payloads
- notes and judgments

## Design rules

- Use `evaluation` only for measurement and scoring.
- Keep evaluation separate from the orchestration of comparisons.
- Make scorer logic explicit and reviewable.
- Preserve enough metadata to explain why a score exists.

## Not the same as

- **Experiment**: comparison and hypothesis testing
- **Benchmark**: reusable test definition
- **Inference**: output generation

## Future role

Evaluation should become a first-class platform surface in Nexus so every
capability can share a common language for quality measurement, regardless of
whether scoring is automated, judge-based, or human-curated.
