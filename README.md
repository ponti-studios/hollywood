# Nexus

[![CI](https://github.com/ponti-studios/nexus/actions/workflows/python-package.yml/badge.svg)](https://github.com/ponti-studios/nexus/actions/workflows/python-package.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Nexus** is an async, typed Python service that acts as a thin adapter between callers and large language models via [OpenRouter](https://openrouter.ai). It exposes a unified REST API for text generation, multi-turn chat, NLP analysis, vision, and model quality evals — all without touching model weights or managing GPU infrastructure.

---

## Why this exists

Most LLM integrations scatter model-calling logic across service code, making it hard to swap providers, test offline, or reason about token usage. Nexus isolates all that into a single FastAPI service with:

- One provider abstraction (`OpenRouterClient`) that async callers depend on
- Pydantic v2 request/response schemas for every endpoint — no raw dicts crossing boundaries
- An eval layer that runs structured quality checks against live model output
- A configuration system that loads `.env` files deterministically and validates every value at startup

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Callers                          │
│             (HTTP clients, scripts, tests)              │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP (JSON / multipart)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI (Nexus)                      │
│                                                         │
│  /health          /text/reply      /text/chat           │
│  /text/analyze    /image/analyze   /evals/run           │
│  /audio/speech    /audio/transcribe                     │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              OpenRouterClient                    │  │
│  │  (httpx.AsyncClient, Authorization header,       │  │
│  │   per-method retry, structured result types)     │  │
│  └───────────────────────┬──────────────────────────┘  │
└──────────────────────────┼──────────────────────────────┘
                           │  HTTPS / OpenAI-compatible API
                           ▼
              ┌────────────────────────┐
              │       OpenRouter       │
              │  (model routing layer) │
              │  anthropic/claude-*    │
              │  openai/gpt-*  etc.    │
              └────────────────────────┘
```

---

## Capabilities

| Route | Method | Description |
|---|---|---|
| `/health` | `GET` | Provider connectivity, active models, capability list |
| `/text/reply` | `POST` | Single-turn prompt → completion |
| `/text/chat` | `POST` | Multi-turn conversation |
| `/text/analyze` | `POST` | Batch NLP: clean text, extract named people |
| `/image/analyze` | `POST` | Vision analysis of an uploaded image |
| `/audio/speech` | `POST` | Text-to-speech → raw MP3 or PCM audio bytes |
| `/audio/transcribe` | `POST` | Speech-to-text: upload audio file, receive transcription |
| `/evals/run` | `POST` | Run the built-in smoke-test eval suite |

Interactive docs at `http://127.0.0.1:8787/docs` when running locally.

---

## Quick start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [mise](https://mise.jdx.dev/) (optional, pins Python + uv versions via `mise.toml`)
- An [OpenRouter API key](https://openrouter.ai/keys)

### Setup

```bash
git clone https://github.com/ponti-studios/nexus.git
cd nexus
uv pip install -e ".[dev]"
cp .env.example .env
# edit .env and set OPENROUTER_API_KEY
```

### Run

```bash
just dev          # hot-reload dev server on :8787
just start        # production server (no reload)
```

Or without `just`:

```bash
uv run python -m uvicorn nexus.api.app:app --reload --host 127.0.0.1 --port 8787
```

---

## Configuration

Copy `.env.example` to `.env`. Only `OPENROUTER_API_KEY` is required.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter API key |
| `OPENROUTER_BASE_URL` | | `https://openrouter.ai/api/v1` | Override for local proxies |
| `OPENROUTER_TEXT_MODEL` | | `anthropic/claude-sonnet-4.6` | Default model for text routes |
| `OPENROUTER_IMAGE_MODEL` | | `anthropic/claude-sonnet-4.6` | Default model for image routes |
| `OPENROUTER_TTS_MODEL` | | `openai/gpt-4o-mini-tts-2025-12-15` | Default model for TTS |
| `OPENROUTER_STT_MODEL` | | `openai/whisper-1` | Default model for STT |

All settings are validated at startup via Pydantic. Invalid or missing required values raise a descriptive error before the server accepts any requests.

---

## API examples

**Single-turn reply**
```bash
curl -X POST http://127.0.0.1:8787/text/reply \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarise the CAP theorem in one sentence."}'
```

**Multi-turn chat**
```bash
curl -X POST http://127.0.0.1:8787/text/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is a deadlock?"},
      {"role": "assistant", "content": "A deadlock is ..."},
      {"role": "user", "content": "Give me a Python example."}
    ]
  }'
```

**Batch NLP analysis**
```bash
curl -X POST http://127.0.0.1:8787/text/analyze \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Lunch with Alice", "Project sync with Bob and Carol"]}'
# → {"results":[{"input":"Lunch with Alice","cleaned_text":"Lunch","people":["Alice"]}, ...]}
```

**Run evals**
```bash
just api-evals
# or:
curl -sS -X POST http://127.0.0.1:8787/evals/run | python -m json.tool
```

**Text-to-speech**
```bash
curl -sS -X POST http://127.0.0.1:8787/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Nexus.", "voice": "alloy"}' \
  --output output.mp3
```
Response is a raw MP3 byte stream (`Content-Type: audio/mpeg`). Use `"response_format": "pcm"` for a low-latency PCM stream.

Available voices (OpenAI models): `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`.

**Speech-to-text**
```bash
curl -sS -X POST http://127.0.0.1:8787/audio/transcribe \
  -F "audio=@recording.mp3"
# → {"text": "...", "model": "openai/whisper-1", "provider": "openrouter",
#     "usage": {"seconds": 11.0, "cost": 0.0011}}
```
Supported formats: `mp3`, `wav`, `flac`, `m4a`, `ogg`, `webm`, `aac`. Format is inferred from the file's MIME type or extension.

---

## Development

```bash
just test        # run test suite
just test-cov    # run with coverage report
just lint        # ruff check
just format      # ruff format + auto-fix
just typecheck   # pyright
just clean       # remove build artefacts
```

### Project layout

```
src/nexus/
├── api/
│   ├── app.py       # FastAPI app, lifespan, all routes
│   └── models.py    # Pydantic request/response schemas
├── evaluation/
│   └── demo.py      # Eval cases, scorers, runner
├── models/
│   └── policy.py    # Active model selection
├── providers/
│   └── openrouter.py # Async HTTP client, error types, result dataclasses
└── env.py           # Settings, dotenv loading, lru_cache singleton
tests/
├── test_api.py      # FastAPI route tests (monkeypatched provider)
├── test_env.py      # Settings loading, validation, dotenv reload
└── test_evals.py    # Eval runner tests (FakeClient)
```

---

## Design decisions

**Why OpenRouter instead of direct vendor SDKs?**
OpenRouter exposes a single OpenAI-compatible endpoint that routes to any model. This keeps `nexus` provider-agnostic: changing `OPENROUTER_TEXT_MODEL` in `.env` switches models without touching code.

**Why not use the OpenAI Python SDK?**
The official SDK adds significant weight and vendor lock-in. A thin `httpx.AsyncClient` wrapper is easier to test, covers exactly the surface area needed, and avoids dependency conflicts.

**Why Pydantic v2 schemas on every boundary?**
Validation at the boundary means route handlers never receive malformed data. Structured response models make it straightforward to version the API without breaking callers.

**Why separate the eval layer?**
Evals are long-running, expensive, and non-idempotent. Keeping them in `evaluation/` (rather than inline in route handlers) makes them independently testable and runnable from the CLI without starting the HTTP server.

---

## What this demonstrates

- **Async Python service design** — FastAPI lifespan, `asyncio.gather` for concurrent NLP batches, full async throughout
- **Multimodal API surface** — text generation, multi-turn chat, NLP extraction, vision, text-to-speech, and speech-to-text unified behind one service and one API key
- **Type-safe API contracts** — Pydantic v2 models, pyright strict checking, no untyped dicts crossing module boundaries
- **Testable architecture** — provider behind a protocol boundary, 100% of routes covered by offline tests via monkeypatching
- **Operational hygiene** — `justfile` task runner, `mise.toml` toolchain pinning, `ruff` lint + format, GitHub Actions CI
- **Evaluation-driven development** — structured eval cases with scorers so model quality is measurable, not subjective

---

## License

[MIT](LICENSE) © Ponti Studios

