# Canonical Schema: Artifact

## Purpose

The artifact schema defines a durable output in Nexus.

Artifacts persist the results of work so they can be referenced, reviewed,
compared, exported, and reused.

## Ownership

Artifacts are a platform primitive shared across capabilities.

## Canonical fields

- `id`: stable artifact ID
- `kind`: one of `model`, `audio`, `image`, `transcript`, `report`, `dataset_export`, `other`
- `capability`: primary capability when relevant
- `producer_run_id`: run that produced the artifact
- `producer_job_id`: optional job that produced the artifact
- `uri`: storage location or local path
- `media_type`: MIME type or equivalent classification
- `metadata`: structured artifact-specific metadata
- `checksum`: optional integrity hash
- `created_at`: artifact creation timestamp

## Example shape

```json
{
  "id": "art_01hxyz...",
  "kind": "audio",
  "capability": "voice",
  "producer_run_id": "run_01hxyz...",
  "producer_job_id": null,
  "uri": ".data/voice/api/runtime/kokoro-abc123/kokoro.wav",
  "media_type": "audio/wav",
  "metadata": {
    "duration_seconds": 3.2,
    "sample_rate_hz": 24000,
    "voice": "af_heart"
  },
  "checksum": null,
  "created_at": 1714600000.0
}
```

## Current fit

Nexus already produces artifacts in practice, including:

- generated audio files
- transcripts
- checkpoint outputs
- benchmark output directories

But these are not yet represented by a first-class shared artifact schema.

## Migration note

Artifacts should become explicit records so Nexus can build durable review,
reporting, lineage, and publishing workflows across all capabilities.
