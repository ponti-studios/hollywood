# Canonical Schema: Run

## Purpose

The run schema defines the atomic execution record for Nexus.

A run should describe one concrete execution event, regardless of whether it is:

- inference
- training
- evaluation
- benchmark execution
- experiment trial

## Ownership

Runs are a platform primitive owned by Nexus, not by a single capability.

## Canonical fields

- `id`: stable run ID
- `kind`: one of `inference`, `training`, `evaluation`, `benchmark`, `experiment_trial`
- `capability`: one of `voice`, `text`, `image`, or another platform capability
- `status`: `pending`, `running`, `completed`, `failed`, `cancelled`
- `model_id`: model used by the run when relevant
- `job_id`: optional parent job ID
- `experiment_id`: optional parent experiment ID
- `evaluation_id`: optional linked evaluation ID
- `benchmark_id`: optional benchmark ID
- `input`: normalized input payload or reference
- `config`: config snapshot used for execution
- `metrics`: structured metrics collected during the run
- `artifact_ids`: artifacts produced by the run
- `error`: structured failure payload when relevant
- `started_at`: execution start timestamp
- `completed_at`: execution completion timestamp
- `created_at`: record creation timestamp

## Example shape

```json
{
  "id": "run_01hxyz...",
  "kind": "inference",
  "capability": "text",
  "status": "completed",
  "model_id": "mlx-community/gemma-4-e2b-bf16",
  "job_id": null,
  "experiment_id": null,
  "evaluation_id": null,
  "benchmark_id": null,
  "input": {
    "messages": [{"role": "user", "content": "Write a tagline."}]
  },
  "config": {
    "temperature": 0.7,
    "max_tokens": 128
  },
  "metrics": {
    "latency_ms": 431.2,
    "prompt_tokens": 18,
    "completion_tokens": 34
  },
  "artifact_ids": [],
  "error": null,
  "started_at": 1714600000.0,
  "completed_at": 1714600000.4,
  "created_at": 1714600000.0
}
```

## Current fit

Current `InferenceRecord` in `src/nexus/api/store.py` is an early subset of this
schema.

## Migration note

The current inference-only store should evolve into a platform-level run schema,
with specialized fields carried in `input`, `config`, and `metrics`.
