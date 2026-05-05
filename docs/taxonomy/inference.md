# Inference

Inference is using a model to produce outputs — text completions, TTS synthesis, STT transcription, image generation.

Current surfaces: `/v1/chat/completions` in `src/nexus/api/routers/inference.py`, plus the audio TTS/STT flows in `src/nexus/audio/service.py`. Both produce durable run records.

Inference produces. Training improves. Evaluation measures.
