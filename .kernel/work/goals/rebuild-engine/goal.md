# Rebuild Nexus engine

## Summary

Rebuild Nexus as a Gemini-first API adapter plus eval layer: keep the public surface small, remove dead compatibility code, and add a real monitoring-friendly eval system instead of a one-off demo.

## Context

The repo has already been stripped down from its training-era architecture. The next step is to finish the rebuild into a durable engine: a stable multimodal adapter with versioned eval runs, raw output retention, and regression monitoring hooks.

## Success Criteria

- [ ] The live API surface is limited to the Gemini-first text, image, and audio routes we intentionally support.
- [ ] Eval runs are versioned and retain raw outputs, scores, and metadata for later inspection.
- [ ] A minimal smoke/regression eval path exists for CI and release gating.
- [ ] Sampled replay, human review, and alert thresholds are represented in the eval design.
- [ ] Dead code, compatibility shims, and obsolete entrypoints are removed from the live tree.

## Epics

- `lock-platform-surfaces`

## Linked Knowledge

- `nexus-hardening-surface-audit`
- `eval-monitoring-practices`

## Journal

- 2026-05-05T20:44:35.437Z: Created goal `stabilize-nexus-platform-before-customization`.
- 2026-05-05: Added hardening criteria after the surface audit.
- 2026-05-05: Training/data schemas, experiment presets, and runtime defaults were hardened to remove hidden customization paths.
- 2026-05-05: Rebuilt Nexus into a Gemini-first API adapter and then removed the CLI and legacy compatibility shims to leave only live product surfaces.
- 2026-05-06: Renamed the goal to `rebuild-engine` and expanded the plan to include versioned eval history, raw output retention, smoke/regression gating, replay, review, and alerting.
