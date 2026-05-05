# Artifact

An artifact is a durable output. Generated audio, transcripts, checkpoints, evaluation reports — things that matter beyond the lifespan of the run that produced them.

The schema lives in `src/nexus/artifacts/schema.py`. A durable store does not yet exist; files are currently tracked by convention under `.data/`. An artifact record links a stable ID, URI, media type, and metadata to the run that produced it.

An artifact persists output. A run records execution. A model is a specific kind of artifact that is also an input to future runs.
