# Nexus Storage Taxonomy

This document defines how Nexus concepts should be stored conceptually.

It is not a final database migration plan. It is the naming and ownership model
for durable platform state so storage evolves coherently across inference,
training, evaluation, and multimodal workflows.

## Design goal

Storage should reflect platform nouns directly.

That means durable state should organize around concepts like:

- models
- runs
- jobs
- evaluations
- experiments
- benchmarks
- artifacts

Avoid letting temporary implementation details become the long-term storage
shape.

## Core storage entities

### Models

Store model identity and metadata.

Examples:

- provider model IDs
- local checkpoints
- adapter lineage
- runtime backend metadata
- capability compatibility

### Runs

Store atomic execution records.

Examples:

- inference runs
- evaluation runs
- training runs
- benchmark runs
- experiment trial runs

### Jobs

Store orchestration lifecycle state.

Examples:

- pending
- running
- failed
- completed
- cancelled

Jobs group and manage work. Runs record execution.

### Evaluations

Store scoring events and judgments.

Examples:

- metric results
- judge outputs
- human review summaries
- benchmark-linked score payloads

### Experiments

Store structured comparisons.

Examples:

- hypothesis
- variants
- participating runs
- summary conclusions
- winners or recommendations

### Benchmarks

Store reusable benchmark definitions and versions.

Examples:

- benchmark ID
- capability
- dataset or prompt set
- expected scorer
- revision/version metadata

### Artifacts

Store durable outputs and reports.

Examples:

- generated media
- transcripts
- checkpoints
- evaluation summaries
- benchmark exports

## Current state in the repo

Today, Nexus stores only a narrow slice of this model explicitly.

### Current durable store

- `src/nexus/api/store.py`
- SQLite file at `.data/api/inference.db`
- table: `inference_runs`

This is a good seed, but it is currently inference-specific rather than
platform-wide.

### Current ephemeral store

- experiment state lives in memory in `src/nexus/api/routers/experiments.py`

This is acceptable for early prototyping, but it is not durable platform state.

## Target storage shape

A future Nexus storage layer should move toward platform-first collections or
tables like:

- `models`
- `runs`
- `jobs`
- `evaluations`
- `experiments`
- `benchmarks`
- `artifacts`

These may later fan out into specialized child tables or indexes, but the core
nouns should remain visible.

## Ownership model

### Platform-owned storage

Should be shared and queryable across capabilities:

- models
- runs
- jobs
- evaluations
- experiments
- artifacts

### Capability-owned storage

May hold domain-specific details that are too specialized for generic platform
schemas.

Examples:

- voice-specific cache directories
- image-specific prompt or mask metadata
- modality-specific worker outputs

These should attach to platform primitives through IDs and metadata, rather than
replacing them.

## Naming rules

### Store nouns, not workflows disguised as tables

Good:

- `runs`
- `evaluations`
- `artifacts`

Avoid:

- `inference_history_log`
- `voice_api_results_store`

### Keep platform entities broad and attach detail through typed fields

For example, a run should capture:

- `kind`
- `capability`
- `config`
- `metrics`
- `artifact_ids`

rather than creating entirely separate storage islands for every workflow too
early.

### Separate durable state from caches

- caches can be capability-specific
- durable platform state should follow the Nexus noun model

## File path guidance

### Durable runtime data

Use `.data/` for persisted local state.

Suggested evolution:

- `.data/models/`
- `.data/runs/`
- `.data/jobs/`
- `.data/evaluations/`
- `.data/artifacts/`

### Capability paths

Capability-specific runtime paths are still useful, for example under:

- `.data/voice/`
- `assets/voice/`
- `research/voice/`

But these should not become the only source of truth for platform records.

## Current-to-target migration direction

### Current

- `InferenceStore`
- `inference_runs`
- in-memory experiments

### Target

- platform-level `RunStore`
- durable experiment storage
- first-class evaluation and artifact storage
- optional job orchestration storage

## Decision rule

When introducing new storage, ask:

1. Is this durable platform state?
2. Which canonical noun owns it?
3. Is this shared across capabilities or capability-specific?
4. Is this a cache, an execution record, or a durable business object?

## Canonical summary

Storage in Nexus should be organized around stable platform nouns, with
capability-specific detail attached to them rather than replacing them.
