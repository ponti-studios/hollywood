# Freeze experiment config and CLI presets

## Summary

Convert experiment execution into a small set of canonical presets instead of a flexible ad hoc runner. The
user should choose from approved paths, not invent a new shape at runtime.

## Context

The experiment subsystem currently exposes the most customization: model roles, backend selection, benchmark
subsets, reference-cache toggles, and CLI overrides. That is too much freedom for a platform we want to
stabilize.

## Acceptance Criteria

- [ ] Experiment config models reject unknown keys.
- [ ] Only canonical experiment presets are available through the public CLI/API path.
- [ ] Benchmarks and model roles follow the approved standard set.
- [ ] Tests cover strict parsing and preset behavior.

## Plan

- Keep the public experiment shapes explicit and finite.
- Remove or isolate ad hoc overrides that are not part of the standard presets.
- Add tests that fail on stray keys or unsupported runtime modes.
- Update the docs/backlog when a new preset is actually justified.

## Checklist

- [ ] Clarify scope and acceptance criteria
- [ ] Implement the core path
- [ ] Verify behavior
- [ ] Capture decisions and follow-ups

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05T20:44:48.074Z: Created task `freeze-experiment-config-and-cli-presets`.
- 2026-05-05: Priority hardening item after config strictness.
- 2026-05-05: Public experiment CLI was frozen to the three standard phase presets; API submission now follows the same preset-only path.
- 2026-05-05: Standalone phase modules were converted to preset-only entrypoints as well.
