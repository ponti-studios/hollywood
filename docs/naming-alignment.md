# Nexus Naming Alignment

This document maps the current codebase to the target Nexus taxonomy.

It exists so we can improve naming intentionally without forcing risky,
large-batch refactors before the platform model is stable.

## Goal

Align package names, API resources, docs, and storage terms with the canonical
Nexus nouns.

## Current → target mapping

### Platform identity

- current: `nexus`
- target: `nexus`
- status: aligned

### Capability identity

- current: `src/nexus/voice`
- target: `src/nexus/voice`
- status: aligned

### API control plane

- current: `src/nexus/api`
- target: `src/nexus/api`
- status: aligned

### Training workflow package

- current: `src/nexus/trainers`
- target: `src/nexus/training`
- status: concept aligned, package name not yet aligned

Rationale: the taxonomy noun is `training`; `trainers` describes one
implementation style.

### Evaluation package

- current: `src/nexus/evaluation`
- target: `src/nexus/evaluation`
- status: aligned

### Experiment package

- current: `src/nexus/experiments`
- target: `src/nexus/experiments`
- status: aligned

### Run storage

- current: `src/nexus/api/store.py`
- target: `src/nexus/runs/store.py` or equivalent platform-owned run subsystem
- status: concept present, ownership boundary not yet aligned

Rationale: runs are a platform primitive, not an API-only concern.

### Runs API

- current: `src/nexus/api/routers/runs.py`
- target: route remains `/v1/runs`, backing ownership may later move to a
  dedicated `nexus.runs` package
- status: route aligned, package ownership not yet aligned

### Experiment persistence

- current: in-memory state inside `src/nexus/api/routers/experiments.py`
- target: durable experiment storage owned by a platform subsystem
- status: not yet aligned

## Recommended package evolution

### Near term

Keep the current package layout, but start introducing platform-first concepts:

- `nexus.runs`
- `nexus.jobs`
- `nexus.artifacts`

These can begin as thin packages if needed.

### Medium term

Rename implementation-biased packages where the concept is broader than the
current name.

Best candidate:

- `nexus.trainers` → `nexus.training`

### Long term

As new capabilities arrive, add new bounded contexts without changing the
platform noun:

- `nexus.text`
- `nexus.image`
- later `nexus.video`, `nexus.music`, `nexus.agents`

## Naming rules

- prefer stable nouns over transient implementation details
- use platform nouns for shared primitives
- use capability nouns for modality-specific domains
- use verbs only for operations, not identity

## Decision rule

Before adding a new module or route, ask:

1. Is this a platform primitive or a capability-specific concern?
2. Is the current name a stable noun or just an implementation detail?
3. Will the name still make sense after the platform adds more modalities?

## Canonical summary

The current repo is already close to the right shape.
The biggest naming gap is not identity, but ownership: some platform primitives
still live in API-specific or implementation-specific locations.
