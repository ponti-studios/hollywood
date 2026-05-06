# Lock platform surfaces

## Summary

Convert the remaining configurable surfaces into canonical platform standards. This epic is the first pass at
eliminating hidden behavior and making the system deterministic by default.

## Context

This epic sits directly under the rebuild-engine goal because it has the best leverage: strict schemas and
frozen presets reduce ambiguity everywhere else. Once these surfaces are locked, the rest of the platform can
build on a much steadier contract.

## Acceptance Criteria

- [ ] Training and experiment config models reject unknown keys.
- [ ] Benchmark selection and runtime presets are canonical rather than free-form.
- [ ] Environment-driven behavior is limited to deployment wiring and secrets.
- [ ] Model loading is restricted to approved paths and backends.

## Plan

1. Tighten config models and add regression tests.
2. Remove free-form CLI and runtime overrides that are not part of the standards.
3. Replace env-driven branching with explicit app wiring where needed.
4. Constrain model/backbone selection to approved paths and fail fast on unsupported modes.
5. Keep the boundaries under test so future changes cannot silently re-open them.

## Tasks

- `make-training-and-data-config-schemas-strict`
- `freeze-experiment-config-and-cli-presets`
- `remove-environment-driven-runtime-customization`
- `constrain-model-loading-to-approved-paths`

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05T20:44:42.123Z: Created epic `lock-platform-surfaces`.
- 2026-05-05: Expanded the epic into an explicit hardening sequence.
- 2026-05-05: Locked experiment CLI/API to presets, removed env-driven runtime wiring, and kept the phase entrypoints preset-only.
