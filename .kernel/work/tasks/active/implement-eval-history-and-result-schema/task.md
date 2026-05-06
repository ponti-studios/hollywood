# Implement eval history and result schema

## Summary

Add durable eval run history so every evaluation has a reproducible record with inputs, outputs, scores, and metadata.

## Context

A useful eval layer needs more than a pass/fail printout. We need structured records that let us compare runs across model versions, prompt versions, and suites without copying data out of chat or terminal output.

## Goal Link

- `rebuild-engine`

## Acceptance Criteria

- [ ] Each eval run stores model/provider identity, suite name, prompt or case identifiers, raw output, score, and timestamp.
- [ ] Result records keep enough metadata to compare candidates against a baseline later.
- [ ] Raw outputs are persisted alongside summary scores.
- [ ] The storage format is simple enough to inspect locally and stable enough to build monitoring on top of.
- [ ] Tests cover save/load behavior for the run history.

## Plan

- Define the eval run/result schema.
- Add a local persistence path for eval history.
- Make result exports include the raw outputs and comparison metadata.
- Lock the schema with tests before layering on dashboards or gates.

## Dependencies

- `eval-monitoring-practices`

## Validation

- `python -m py_compile` on the live eval modules
- `python -m pytest`

## Linked Knowledge

- `eval-monitoring-practices`
- `nexus-hardening-surface-audit`

## Journal

- 2026-05-06: Created task `implement-eval-history-and-result-schema`.
