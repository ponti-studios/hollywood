# Implement batch NLP route for text arrays

## Summary

Add a batch text analysis route that accepts an array of short texts and returns per-item NLP output for cleanup and people extraction.

## Context

This gives Nexus a useful standalone service shape for the name-drop use case: clients can send multiple texts in one request and receive normalized summaries and extracted people without needing persistence or a separate app.

## Goal Link

- `rebuild-engine`

## Acceptance Criteria

- [x] The batch text route accepts a non-empty array of input strings.
- [x] Each input produces a corresponding analysis object in the same order.
- [x] The response includes cleaned text and extracted people for each item.
- [x] Invalid payloads fail fast with schema validation instead of ad hoc parsing.
- [x] Tests cover the happy path, empty-array rejection, and malformed payload handling.

## Plan

- Define request/response models for batch text analysis.
- Add the route to the FastAPI app and wire it through the existing Gemini-backed text layer.
- Return one result per input text with stable ordering.
- Add tests for success and validation behavior.
- Document the new route in the API surface docs.

## Dependencies

- `nexus-hardening-surface-audit`

## Validation

- `python -m py_compile src/nexus`
- `python -m pytest`

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-08: Created task `implement-batch-nlp-route-for-text-arrays`.
- 2026-05-08: Added the `/text/analyze` batch route, strict request/response models, Gemini-backed per-item cleanup and people extraction, and validation coverage for empty and malformed payloads.
- 2026-05-08: Archived after validation and migration into Nexus; the standalone `nlp_benchmark` repo was removed.
