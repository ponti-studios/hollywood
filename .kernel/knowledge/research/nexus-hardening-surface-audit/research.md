# Nexus hardening surface audit

## Research

This audit maps the remaining customization surfaces that can change Nexus behavior without a code review.
The platform is already improving, but several paths still let behavior drift through YAML, environment variables,
or alternate execution modes.

## Context

This is the durable companion to the hardening backlog. It records what the scan found so the team can lock
surfaces down in a controlled order instead of rediscovering the same gaps later.

## Details

### Findings

- **Training config is now moving toward strict standards**, but the repo still needs the same treatment across
  the rest of the config layer.
- **Experiment config remains the largest customization surface**:
  - benchmark subsets can be changed per run
  - reference-cache behavior can be toggled per run
  - the experiment runtime still supports alternate inference backends
- **Environment variables still drive behavior** in several services:
  - text worker model identity / autoload behavior
  - API backend URLs
  - audio worker role selection
  - experiment runner remote backend auth
- **Model loading still crosses a trust boundary** via Hugging Face model loading for approved models.
- **Dataset loading is now much cleaner** because remote-code dataset loading has been removed from the main paths.

### Hardening order

1. Make config schemas strict and reject unknown keys everywhere.
2. Freeze experiment presets and remove per-run behavioral overrides.
3. Reduce env-driven runtime branching to deployment wiring only.
4. Constrain model loading paths to approved identifiers and adapters.
5. Keep the lock-in enforced with tests so drift is visible immediately.

### Current progress

- Training/data config models are now strict.
- Experiment config models are now strict.
- The public experiment CLI and API now load only the fixed phase presets from configs/benchmarks/.
- The standalone phase CLIs now also load their fixed presets instead of accepting ad hoc flags.
- The alternate openai-compatible experiment backend has been removed.
- Runtime env-driven wiring has been eliminated from the user-facing service/app defaults.
- Model-loading paths no longer opt into remote code execution for standard paths.
- The approved loaders now rely on standard Transformers code paths only.
- Regression tests cover unknown-key rejection for the hardened config paths.

## Links

- Goal: `stabilize-nexus-platform-before-customization`
- Epic: `lock-platform-surfaces`
- Tasks:
  - `make-training-and-data-config-schemas-strict`
  - `freeze-experiment-config-and-cli-presets`
  - `remove-environment-driven-runtime-customization`
  - `constrain-model-loading-to-approved-paths`
