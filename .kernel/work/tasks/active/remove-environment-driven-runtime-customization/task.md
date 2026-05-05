# Remove environment-driven runtime customization

## Summary

Stop using environment variables as a general behavior switchboard. Runtime wiring should come from explicit
deployment configuration or constructor arguments, not from hidden per-process branching.

## Context

The scan found several places where env vars affect model identity, backend URLs, worker roles, or remote
backend auth. Those are useful during exploration, but they make the platform less predictable.

## Acceptance Criteria

- [ ] User-facing runtime behavior no longer depends on ad hoc env toggles.
- [ ] Service wiring is explicit and deterministic.
- [ ] Any remaining env use is limited to deployment-level secrets or host wiring.
- [ ] Tests verify the standard runtime path without custom env branching.

## Plan

- Replace env-driven switches with explicit app wiring where possible.
- Keep only the minimal host-level settings that are genuinely deployment concerns.
- Make unsupported runtime modes fail fast rather than falling back.
- Add tests that lock the expected default wiring.

## Checklist

- [ ] Clarify scope and acceptance criteria
- [ ] Implement the core path
- [ ] Verify behavior
- [ ] Capture decisions and follow-ups

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05T20:44:48.075Z: Created task `remove-environment-driven-runtime-customization`.
- 2026-05-05: Runtime env branching identified as a long-term stability risk.
- 2026-05-05: Removed env-driven wiring from API backends, text/audio app defaults, and evaluation helpers; defaults are now fixed in code.
