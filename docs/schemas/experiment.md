# Canonical Schema: Experiment

## Purpose

The experiment schema defines a structured comparison in Nexus.

Experiments answer questions like:

- which variant performed better?
- did a configuration change improve quality?
- should we ship model A or model B?

## Ownership

Experiments are a platform primitive used by research, evaluation, and product
teams.

## Canonical fields

- `id`: stable experiment ID
- `name`: human-readable name
- `hypothesis`: the question being tested
- `capability`: primary capability under study
- `status`: `pending`, `running`, `completed`, `failed`, `cancelled`
- `benchmark_ids`: benchmarks used in the comparison
- `variant_specs`: the variants being compared
- `run_ids`: runs belonging to the experiment
- `evaluation_ids`: evaluations produced by or attached to the experiment
- `summary`: structured summary of outcomes
- `winner`: optional winning variant ID or recommendation
- `created_at`: creation timestamp
- `started_at`: execution start timestamp
- `completed_at`: completion timestamp

## Example shape

```json
{
  "id": "exp_01hxyz...",
  "name": "tts-engine-comparison-apr",
  "hypothesis": "Kokoro produces more natural output than baseline engine on studio prompts.",
  "capability": "voice",
  "status": "completed",
  "benchmark_ids": ["voice_naturalness_v1"],
  "variant_specs": [
    {"id": "kokoro", "model_id": "nexus-kokoro-tts"},
    {"id": "baseline", "model_id": "baseline-tts"}
  ],
  "run_ids": ["run_01", "run_02", "run_03"],
  "evaluation_ids": ["eval_01", "eval_02"],
  "summary": {
    "winner": "kokoro",
    "confidence": "medium"
  },
  "winner": "kokoro",
  "created_at": 1714600000.0,
  "started_at": 1714600010.0,
  "completed_at": 1714601200.0
}
```

## Current fit

Current experiment records are in-memory in `src/nexus/api/routers/experiments.py`.
The current shape captures status and config, but not yet the full durable
platform schema.

## Migration note

Experiments should move to durable storage and explicitly reference runs,
evaluations, benchmarks, and summaries.
