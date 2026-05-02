# Inference

## What it means

Inference is the act of using a model to produce outputs.

Examples include:

- text completion
- chat response generation
- image generation
- text-to-speech synthesis
- speech-to-text transcription

Inference is an operational workflow.
It is about producing outputs, not comparing them.

## How it fits in the platform

Inference is one of the core execution surfaces of Nexus.

It sits between:

- model assets
- capability-specific logic
- output artifacts
- run tracking
- downstream evaluation

Inference is the part of the platform that turns models into usable creative
behavior.

## How it works in Nexus

Inference should produce:

- outputs
- timing and token metadata
- run records
- optional persisted artifacts

Current examples include:

- `/v1/chat/completions` in `src/nexus/api/routers/inference.py`
- voice TTS and STT flows in `src/nexus/voice/service.py`

Over time, each capability should expose inference surfaces through Nexus while
sharing common run and metadata conventions.

## Design rules

- Use `inference` for generation or execution.
- Do not use `inference` as a synonym for evaluation or experimentation.
- Inference should record operational metadata such as latency, tokens, model,
  and parameters.
- Inference results should be easy to feed into evaluation and experiments.

## Not the same as

- **Evaluation**: scoring outputs
- **Experiment**: comparing variants
- **Training**: updating model parameters

## Future role

Inference should become a consistent cross-capability contract in Nexus, with
shared run semantics and capability-specific adapters for text, image, voice,
and future modalities.
