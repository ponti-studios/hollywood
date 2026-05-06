# Nexus

Nexus is a Gemini-first multimodal API adapter and eval layer.

It does **not** host models.

- **Text** requests go to **Gemini**
- **Audio** requests go to **Gemini**
- **Image** requests go to **Gemini**
- **Evals** run as a small demo suite to show model comparison workflows

## What ships

### API
- `POST /text/reply`
- `POST /text/chat`
- `POST /image/analyze`
- `POST /audio/tts`
- `POST /audio/stt`
- `GET /health`

## Environment

Copy `.env.example` to `.env` and fill in your Gemini key.

### Required
- `GEMINI_API_KEY`

### Optional
- `GEMINI_BASE_URL`
- `GEMINI_TEXT_MODEL`
- `GEMINI_AUDIO_MODEL`
- `GEMINI_IMAGE_MODEL`
- `GEMINI_SPEECH_VOICE`

## Run locally

```bash
uv pip install -e .
cp .env.example .env
python -m uvicorn nexus.api.app:app --reload
```

## Notes

- No training code.
- No local model hosting.
- All model calls are delegated to Gemini.
