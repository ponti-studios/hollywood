# Nexus Storage Model

Nexus persists durable platform state in a local SQLite database at `.data/api/inference.db`. New durable concepts get a `schema.py` and `store.py` in their owning package.

## What is stored today

**Runs** (`src/nexus/runs/`) — atomic execution records for inference and other workflows.

**Experiments** (`src/nexus/experiments/`) — comparison records with status, config snapshot, scores, and evaluation linkage.

**Evaluations** (`src/nexus/evaluation/`) — quality measurement records linked to runs, experiments, and benchmarks.

## What is not stored yet

**Jobs**, **Artifacts**, and **Models** have schemas in their owning packages but no stores yet.

## Three kinds of storage to keep separate

**Platform records** are durable, queryable, keyed by stable IDs. These belong in stores. Examples: runs, experiments, evaluations.

**Capability files and caches** are modality-specific outputs that live in `.data/audio/`, `assets/audio/`, benchmark cache dirs, and so on. These are useful but are not the system of record.

**Research outputs** in `research/` are exploratory and disposable. They inform the platform but don't define its data model.

A file on disk is not a platform record. A generated wav file is a file. An artifact record with a URI pointing to that file is a platform record.

## How to add new durable storage

Put `schema.py` and `store.py` in the owning package. Write tests. Use the shared SQLite database unless there is a strong reason not to.
