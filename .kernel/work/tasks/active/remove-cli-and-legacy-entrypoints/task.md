# Remove CLI and legacy entrypoints

## Summary

Delete the Nexus CLI package and every legacy entrypoint that existed only to support the old command surface.

## Context

Nexus is now a Gemini-first API adapter and demo eval layer. The CLI no longer provides unique product value, so keeping it around would only preserve dead surface area and extra packaging complexity.

## Goal Link

- `rebuild-engine`

## Acceptance Criteria

- [x] `nexus` console script is removed.
- [x] CLI package modules are deleted.
- [x] README and packaging no longer mention the CLI.
- [x] Import and test paths no longer depend on CLI entrypoints.
- [x] Live API/eval behavior continues to pass validation.

## Plan

- Remove the CLI package and its module entrypoint.
- Remove the project script wiring from packaging.
- Update docs so the published surface matches the code.
- Re-run compile and tests against the reduced tree.

## Dependencies

- `remove-environment-driven-runtime-customization`

## Validation

- `python -m py_compile` on the live source files
- `python -m pytest`

## Linked Knowledge

- `nexus-hardening-surface-audit`

## Journal

- 2026-05-05: Created task `remove-cli-and-legacy-entrypoints`.
- 2026-05-05: Deleted the CLI package, removed the console script, and trimmed packaging/docs to the live API/eval surface.
