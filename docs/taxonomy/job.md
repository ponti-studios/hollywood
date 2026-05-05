# Job

A job is the orchestration wrapper around work that needs lifecycle management — queueing, retries, cancellation, progress tracking. A job may create one or many runs.

The schema lives in `src/nexus/jobs/schema.py`. A durable store does not yet exist.

Use a job when you care about managed work lifecycle. Use a run when you care about what executed and what it produced.
