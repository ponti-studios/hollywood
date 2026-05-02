# Job

## What it means

A job is an orchestrated unit of work.

Jobs are used when Nexus needs lifecycle management around execution, such as:

- queueing
- scheduling
- retries
- cancellation
- progress tracking
- worker assignment

A job may create one or many runs.

## How it fits in the platform

Jobs sit above runs.

They are the platform abstraction for managed work, especially when workflows
become too heavy or too asynchronous to treat as simple request-response
operations.

Typical examples:

- training job
- batch evaluation job
- benchmark job
- export job
- multimodal generation job

## How it works in Nexus

Nexus does not yet have a full job subsystem, but it should.

A future job layer would likely manage:

- job type
- submitted config
- execution status
- related run IDs
- result summaries
- failure and retry state

Jobs should provide the operator-facing view of long-running work.
Runs should provide the execution-level audit trail.

## Design rules

- Use `job` when orchestration and lifecycle matter.
- Use `run` when recording a concrete execution.
- A job may have many runs.
- Jobs should expose clear status transitions.

## Not the same as

- **Run**: one execution record
- **Experiment**: comparison logic
- **Training**: a workflow type that may be implemented as a job

## Future role

Jobs are the natural next step once Nexus moves beyond lightweight local
orchestration into durable platform operations for training, evaluation, and
batch creative generation.
