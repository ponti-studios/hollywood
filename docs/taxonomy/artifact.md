# Artifact

## What it means

An artifact is a durable output produced by the platform.

Examples include:

- model checkpoint
- adapter weights
- generated image
- generated audio file
- transcript
- evaluation report
- experiment summary
- benchmark result export

Artifacts are the persisted outputs that runs and jobs leave behind.

## How it fits in the platform

Artifacts are how Nexus turns work into durable value.

They allow the platform to:

- inspect past outputs
- compare results over time
- reuse generated assets
- attach reports to runs and experiments
- preserve model lineage

Artifacts link execution history to usable assets.

## How it works in Nexus

Current examples include:

- generated voice outputs under runtime and asset paths
- training outputs in `.data/checkpoints/*`
- stored run metadata and benchmark outputs

Over time, Nexus should treat artifacts more explicitly with metadata like:

- artifact ID
- artifact kind
- producing run ID
- storage location
- media type
- checksum or version
- lineage metadata

## Design rules

- Persist important outputs as artifacts, not just ephemeral files.
- Artifacts should be attributable to a run or job.
- Artifact metadata should be stable enough for indexing and retrieval.
- Distinguish artifacts from models when needed; some models are also artifacts,
  but not all artifacts are models.

## Not the same as

- **Run**: execution record
- **Model**: a specific asset class used by workflows
- **Evaluation**: scoring metadata that may itself produce report artifacts

## Future role

Artifacts are the memory of the Nexus platform.
They will be essential for reproducibility, creative review, model lineage, and
productizing generated outputs across the studio.
