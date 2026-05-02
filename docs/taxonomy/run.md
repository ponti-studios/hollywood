# Run

## What it means

A run is a single execution record.

Examples include:

- one inference request
- one benchmark pass
- one experiment trial
- one training execution
- one evaluation pass

The run is the atomic operational record of work in Nexus.

## How it fits in the platform

Runs are one of the most important platform primitives because they connect:

- what was executed
- with what inputs and config
- against which model
- at what time
- with what outputs and metrics

Every higher-level workflow should be understandable in terms of runs.

## How it works in Nexus

Nexus already has an early run ledger in:

- `src/nexus/api/store.py`
- `src/nexus/api/routers/runs.py`

That should evolve into a broader cross-platform run system that can represent:

- inference runs
- training runs
- evaluation runs
- benchmark runs
- experiment trials

## Design rules

A run should eventually carry fields like:

- ID
- kind
- capability
- model ID
- status
- config snapshot
- timestamps
- metrics
- artifact references
- parent job or experiment IDs when relevant

## Not the same as

- **Job**: orchestration wrapper around work
- **Experiment**: a collection of compared runs
- **Artifact**: a persisted output produced by a run

## Future role

Runs should become the common record format across the Nexus platform.
Once this is standardized, reporting, debugging, comparison, evaluation, and
operator tooling become much easier to scale.
