# Nexus

Nexus is an OpenAI-first multimodal API adapter and eval layer.

It does **not** host models.

- **Text** requests go to **OpenAI**
- **Audio** requests go to **OpenAI**
- **Image** requests go to **OpenAI**
- **NLP**
  - performs natural language processing on arrays of texts to provide clean summaries and extract people
- **Evals** run as a small demo suite to show model comparison workflows

## What ships

### API

- `POST /text/reply`
- `POST /text/chat`
- `POST /text/analyze`
- `POST /image/analyze`
- `POST /audio/tts`
- `POST /audio/stt`
- `GET /health`

## Environment

Copy `.env.example` to `.env` and set your OpenAI API key.

### Required

- `OPENAI_API_KEY`

### Optional

- `OPENAI_BASE_URL`
- `OPENAI_TEXT_MODEL`
- `OPENAI_IMAGE_MODEL`
- `OPENAI_TTS_MODEL`
- `OPENAI_STT_MODEL`
- `OPENAI_SPEECH_VOICE`

## Run locally

```bash
uv pip install -e .
cp .env.example .env
python -m uvicorn nexus.api.app:app --reload
```

## Notes

- No training code.
- No local model hosting.
- All model calls are delegated to OpenAI.
