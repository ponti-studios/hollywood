# Nexus Naming Alignment

This document maps the current codebase to the target Nexus taxonomy. Use it before adding new packages, routes, or storage.

## Current package alignment

| Concept | Current package | Status |
|---|---|---|
| Platform | `nexus` | aligned |
| Audio capability | `src/nexus/audio` | aligned |
| API control plane | `src/nexus/api` | aligned |
| Run records | `src/nexus/runs` | aligned |
| Evaluation | `src/nexus/evaluation` | aligned |
| Experiments | `src/nexus/experiments` | aligned |
| Jobs | `src/nexus/jobs` | schema only, no store yet |
| Artifacts | `src/nexus/artifacts` | schema only, no store yet |
| Training workflows | `src/nexus/trainers` | concept aligned, package name is `trainers` not `training` |

## Open naming gap

`src/nexus/trainers` should eventually become `src/nexus/training`. The taxonomy noun is `training`; `trainers` is an implementation detail. This is the one package name that still drifts from the noun model.

## Rules

- Use stable nouns, not implementation details or transport terms.
- Platform primitives belong in owning packages with `schema.py` and `store.py`.
- Capability names (`audio`, `text`, `image`) describe product domains, not the platform.
- The top-level service and repo identity is always `nexus`.
