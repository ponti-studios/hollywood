# Nexus

Nexus is an OpenRouter-first multimodal API adapter and eval layer.

It does **not** host models.

- **Text** requests go to **OpenRouter**
- **Image** requests go to **OpenRouter**
- **NLP**
  - performs natural language processing on arrays of texts to provide clean summaries and extract people
- **Evals** run as a small demo suite for basic smoke testing

## What ships

### API

- `POST /text/reply`
- `POST /text/chat`
- `POST /text/analyze`
- `POST /image/analyze`
- `GET /health`

## Environment

Copy `.env.example` to `.env` and set your OpenRouter API key.
This project runs as a normal Python app; Docker is not required.

### Required

- `OPENROUTER_API_KEY`

### Optional

- `OPENROUTER_BASE_URL`
- `OPENROUTER_TEXT_MODEL`
- `OPENROUTER_IMAGE_MODEL`

## Run locally

```bash
uv pip install -e ".[dev]"
cp .env.example .env
uv run python -m uvicorn nexus.api.app:app --reload --host 127.0.0.1 --port 8787
```

Or with `just`:

```bash
just dev
```

For a non-reloading server:

```bash
just start
```

## Notes

- No training code.
- No dataset download pipeline.
- No experiment runner or model fine-tuning workflow.
- No local model hosting.
- All model calls are delegated to OpenRouter.
