# Constrain model loading to approved paths

## Summary

Make model loading follow a single approved path, with only the backed models and adapters that we have decided
are part of the platform. Unsupported backends or code-execution shortcuts should fail fast.

## Context

Model loading remains the main trust boundary in the system. Hugging Face model loading is already a controlled
boundary, but alternate backends and custom loading shapes increase the surface area.

## Acceptance Criteria

- [x] Approved model loading paths are explicit.
- [x] Unsupported backend modes fail fast.
- [x] Trust boundaries are documented and tested.
- [x] The standard training and inference paths keep working.

## Plan

- Enumerate the supported loading paths and keep them narrow.
- Isolate or remove alternate backend behavior that is not part of the standard platform.
- Keep model loading tests focused on the approved paths.
- Avoid introducing new loader escapes without a dedicated decision record.

## Checklist

- [ ] Clarify scope and acceptance criteria
- [ ] Implement the core path
- [ ] Verify behavior
- [ ] Capture decisions and follow-ups

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05T20:44:48.074Z: Created task `constrain-model-loading-to-approved-paths`.
- 2026-05-05: Model loading trust boundary added to the hardening backlog.
- 2026-05-05: Standard loaders and pipelines no longer opt into remote code execution on the approved paths.
- 2026-05-05: Verified by tests that capture loader and pipeline kwargs.
