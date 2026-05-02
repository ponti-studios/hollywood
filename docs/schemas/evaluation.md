# Canonical Schema: Evaluation

## Purpose

The evaluation schema defines a measurement event in Nexus.

An evaluation records how a subject was scored, by what rubric or scorer, and
with what results.

## Ownership

Evaluations are a platform primitive owned by Nexus and used by all
capabilities.

## Canonical fields

- `id`: stable evaluation ID
- `subject_type`: one of `run`, `model`, `artifact`
- `subject_id`: ID of the thing being evaluated
- `capability`: primary capability
- `benchmark_id`: optional benchmark ID
- `scorer`: scorer identity, such as a metric function, judge model, or human reviewer
- `rubric`: optional rubric or evaluation policy reference
- `metrics`: structured score payload
- `judgment`: optional qualitative summary or class label
- `notes`: optional review notes
- `created_at`: evaluation creation timestamp

## Example shape

```json
{
  "id": "eval_01hxyz...",
  "subject_type": "run",
  "subject_id": "run_01hxyz...",
  "capability": "voice",
  "benchmark_id": "voice_naturalness_v1",
  "scorer": "judge:gpt-4.1",
  "rubric": "voice-naturalness-rubric-v1",
  "metrics": {
    "naturalness": 4.4,
    "pronunciation": 4.7,
    "artifact_rate": 0.02
  },
  "judgment": "high quality with minor pronunciation issues",
  "notes": "Strong pacing; slight issue on named entity.",
  "created_at": 1714600000.0
}
```

## Current fit

Evaluation logic currently exists in `src/nexus/evaluation/*`, but there is not
yet a first-class persisted evaluation resource.

## Migration note

Evaluations should become explicit records so experiments, reporting, and human
review can all reference the same quality objects.
