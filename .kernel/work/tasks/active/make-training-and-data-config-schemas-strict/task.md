# Make training and data config schemas strict

## Summary

Lock the training-side config models so they only accept known, canonical fields. This removes accidental
configuration drift and makes YAML failures obvious immediately.

## Context

This task is the first low-risk hardening step. Data config is already becoming strict, and the same contract
needs to apply to the rest of the training config models so there is one accepted schema.

## Acceptance Criteria

- [ ] Training-related config models reject unknown keys.
- [ ] Recipe-level config rejects unknown keys.
- [ ] Validation tests prove the strictness contract.
- [ ] Existing standard recipes still load successfully.

## Plan

- Add `extra="forbid"` to the training config models that still allow stray keys.
- Keep the public fields, but do not allow arbitrary additions.
- Add regression tests for unknown-key rejection.
- Verify that the current recipes still validate without edits.

## Checklist

- [ ] Clarify scope and acceptance criteria
- [ ] Implement the core path
- [ ] Verify behavior
- [ ] Capture decisions and follow-ups

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05T20:44:48.075Z: Created task `make-training-and-data-config-schemas-strict`.
- 2026-05-05: Hardening work started; config strictness is the first lock surface.
- 2026-05-05: Training/data/recipe config models were made strict; unknown-key regression tests were added.
