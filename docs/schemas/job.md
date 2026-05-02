# Canonical Schema: Job

## Purpose

The job schema defines managed work in Nexus.

Jobs exist when the platform needs orchestration semantics such as:

- queueing
- retries
- progress tracking
- cancellation
- worker dispatch

A job may produce one or many runs.

## Ownership

Jobs are a platform primitive owned by Nexus.

## Canonical fields

- `id`: stable job ID
- `kind`: one of `training`, `evaluation`, `benchmark`, `export`, `batch_inference`
- `capability`: primary capability when relevant
- `status`: `queued`, `running`, `completed`, `failed`, `cancelled`
- `requested_by`: actor or system that submitted the job
- `config`: submitted job config snapshot
- `run_ids`: runs created under the job
- `result_summary`: compact summary of output or outcome
- `error`: structured failure payload when relevant
- `progress`: optional progress metadata
- `created_at`: submission timestamp
- `started_at`: execution start timestamp
- `completed_at`: execution completion timestamp

## Example shape

```json
{
  "id": "job_01hxyz...",
  "kind": "training",
  "capability": "text",
  "status": "running",
  "requested_by": "user:charles",
  "config": {
    "recipe": "configs/recipes/sft_lora.yaml"
  },
  "run_ids": ["run_01", "run_02"],
  "result_summary": null,
  "error": null,
  "progress": {
    "step": 420,
    "total_steps": 1000
  },
  "created_at": 1714600000.0,
  "started_at": 1714600010.0,
  "completed_at": null
}
```

## Current fit

Nexus does not yet have a first-class job subsystem.
This schema is the target shape for orchestration-grade workflows.

## Migration note

Jobs should eventually become the parent records for long-running training,
evaluation, benchmark, and batch generation workflows.
