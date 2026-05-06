# Implement eval suites, CI gates, and review loop

## Summary

Add the monitoring layer around evals: smoke suites, regression checks, replay-friendly exports, human review hooks, and alert thresholds.

## Context

Once eval history exists, the next step is to make it operational. That means a small suite for fast checks, a larger regression path for release confidence, and exportable artifacts that support replay and manual review.

## Goal Link

- `rebuild-engine`

## Acceptance Criteria

- [ ] A smoke eval suite can run quickly in CI.
- [ ] A regression suite can compare candidate runs against a baseline.
- [ ] The eval output includes enough detail for sampled replay and human review.
- [ ] Alert or threshold logic is represented for failure spikes, latency spikes, or score regressions.
- [ ] Tests cover the reporting/export shape for the suites.

## Plan

- Split evals into smoke and regression tiers.
- Add baseline comparison helpers.
- Add a replay/export format suitable for human review.
- Define simple threshold/alert hooks that can be wired into CI or release checks later.

## Dependencies

- `implement-eval-history-and-result-schema`
- `eval-monitoring-practices`

## Validation

- `python -m py_compile` on the live eval modules
- `python -m pytest`

## Linked Knowledge

- `eval-monitoring-practices`
- `nexus-hardening-surface-audit`

## Journal

- 2026-05-06: Created task `implement-eval-suites-ci-gates-and-review-loop`.
