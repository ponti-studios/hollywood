# Model

A model is an asset the platform operates on. It may be a hosted model ID, a local checkpoint, a fine-tuned adapter, or a quantized runtime variant. Models are consumed by inference, evaluation, and experiments, and produced by training.

Current model loading lives in `src/nexus/models/`. A first-class durable model registry does not yet exist; model identity is currently tracked by string ID.

A model is an asset. A run uses a model. Training may produce one.
