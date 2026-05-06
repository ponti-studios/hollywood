# Eval monitoring practices

## Research

This note captures the common patterns teams use to monitor model evals over time.

## Context

Nexus is becoming a Gemini-first adapter plus eval layer. To make the eval layer useful, it needs more than a one-off demo: it needs durable history, comparable runs, and a way to catch regressions before they hit users.

## Details

### Findings

- **Version every eval run** with model, prompt set, dataset/suite, scoring method, and timestamp.
- **Store raw outputs**, not only aggregate scores, so failures can be inspected later.
- **Track a small set of metrics** by task, such as pass rate, exact match, formatting validity, refusal rate, latency, and token cost.
- **Compare against baselines** so regressions are visible when a candidate model, prompt, or provider changes.
- **Run smoke suites in CI** and block releases when core metrics regress below a threshold.
- **Sample real traffic for replay** when the team wants to compare production behavior against the latest prompt/model.
- **Use human review** for subjective tasks and for validating automatic scoring quality.
- **Alert on spikes and drift** in failures, latency, or provider errors.
- **Organize suites by task** instead of one monolithic score, so changes are easier to localize.

### Practical shape

A minimal monitoring stack usually needs:

1. a run record store or JSON history
2. saved outputs and scores per case
3. a small smoke suite for CI
4. a baseline comparison path
5. an export format for human review
6. threshold checks for alerts or release gates

## Links

- Goal: `rebuild-engine`
- Tasks:
  - `implement-eval-history-and-result-schema`
  - `implement-eval-suites-ci-gates-and-review-loop`
