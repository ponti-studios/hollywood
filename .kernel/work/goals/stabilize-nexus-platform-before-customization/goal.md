# Stabilize Nexus platform before customization

## Summary

Make Nexus behave like a standards-driven platform: fixed schemas, fixed presets, and explicit integration
boundaries. Customization should be rare, reviewed, and intentional rather than hidden in YAML or env vars.

## Context

The hardening audit showed that the platform still has several places where behavior can drift outside the
canonical path. That is acceptable while we are exploring, but not if we want a stable team-wide platform.
This goal exists to freeze the public surfaces before any more customization is allowed.

## Success Criteria

- [ ] Config models reject unknown keys across training and experiment paths.
- [ ] Public workflows use canonical presets instead of ad hoc per-run overrides.
- [ ] Runtime branching through environment variables is reduced to deployment wiring, not user-facing behavior.
- [ ] Model loading paths are constrained to approved backends and identifiers.

## Epics

- `lock-platform-surfaces`

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05T20:44:35.437Z: Created goal `stabilize-nexus-platform-before-customization`.
- 2026-05-05: Added hardening criteria after the surface audit.
- 2026-05-05: Training/data schemas, experiment presets, and runtime defaults were hardened to remove hidden customization paths.
