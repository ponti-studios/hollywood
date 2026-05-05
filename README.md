# nexus — Multimodal Inference, Training, and Evaluation Platform

Nexus is the control plane for multimodal generative systems.

Today, the repo contains three closely related layers:

- a public FastAPI control plane for text, audio, runs, and experiments
- private text and audio worker services behind that API
- local training, evaluation, and benchmark workflows for posttraining experiments

The canonical product language and implementation contracts live here:

- `docs/taxonomy/nexus.md` — what Nexus is
- `docs/taxonomy/README.md` — the canonical noun model
- `docs/api-taxonomy.md` — how nouns map to routes
- `docs/storage-model.md` — what counts as durable platform state
- `src/nexus/*/schema.py` — package-owned schemas

## Platform Shape

Nexus uses a simple rule:

- platform resources live at `/v1/{noun}`
- capability actions live at `/v1/{capability}/{action}`

Examples that exist today:

- `POST /v1/chat/completions`
- `GET /v1/audio/health`
- `POST /v1/audio/tts`
- `POST /v1/audio/transcribe`
- `GET /v1/runs`
- `GET /v1/runs/{id}`
- `GET /v1/experiments`
- `POST /v1/experiments`

Examples defined in the taxonomy but not yet exposed:

- `/v1/evaluations`
- `/v1/jobs`
- `/v1/artifacts`
- `/v1/benchmarks`

## Storage Model

Nexus keeps durable platform records in a shared SQLite database at
`.data/api/inference.db`.

Stored today:

- `runs` — the canonical run ledger
- `experiments` — benchmark comparisons and summaries
- `evaluations` — quality measurements linked to runs and experiments

Not stored yet as first-class tables:

- `jobs`
- `artifacts`
- `models`

Capability-specific files and caches still exist on disk, but they are not the
system of record.

---

## What is posttraining?

Posttraining is everything that happens *after* a large language model is
initially trained on massive amounts of text. The base model knows a lot about
language and the world, but it doesn't know how to be helpful, follow instructions,
or avoid harmful outputs. Posttraining teaches it those things.

The main techniques, roughly in order of complexity:

| Method | What it teaches | Data needed |
|--------|----------------|-------------|
| **SFT** | How to follow instructions | (prompt, response) pairs |
| **DPO** | Which responses are better | (prompt, chosen, rejected) triples |
| **ORPO** | SFT + preferences in one pass | Same as DPO |
| **GRPO** | How to reason (DeepSeek R1 style) | Prompts + a reward function |

---

## Setup

### Prerequisites

- [mise](https://mise.jdx.dev/) for pinned tool versions
- Apple Silicon Mac (M1 Pro/Max or M2/M3 recommended)
- Python 3.12.x for the Apple runtime stack
- [uv](https://docs.astral.sh/uv/) for package management
- A free [HuggingFace account](https://huggingface.co) + API token
- A free [Weights & Biases account](https://wandb.ai) for experiment tracking

### Install

```bash
# Clone the repo
git clone <your-repo-url>
cd nexus

# Install the exact toolchain pinned in mise.toml
mise install

# Cross-platform dev install: tests, linting, notebooks, config/data utilities
mise exec -- uv venv .venv
uv pip install -e ".[dev,notebook]"

# Full Apple Silicon runtime install: training and eval
uv pip install -e ".[dev,notebook,apple]"

# Or use the Makefile shortcuts
make setup
make setup-apple

# Copy and fill in your API keys
cp .env.example .env
# Edit .env: add HF_TOKEN and WANDB_API_KEY
```

`make setup` is intentionally cross-platform and does not install the Apple-only
runtime stack. Training and perplexity evaluation require the `apple` extra on
Apple Silicon, and the CLI now guards those commands so they fail early if
Python, platform, or optional runtime dependencies are wrong.

### Start the Nexus runtime

```bash
# Start the full runtime graph
docker compose up --build -d

# Follow logs for the public API and private model workers
just nexus-logs

# Check health
just nexus-health
```

With the compose stack up, the public API is the only endpoint you need:

- OpenAPI schema: `http://localhost:8787/openapi.json`
- Interactive docs: `http://localhost:8787/docs`
- Redoc: `http://localhost:8787/redoc`

```bash
# Text generation
curl -sS -X POST http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "HuggingFaceTB/SmolLM2-135M-Instruct",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }'

# Speaker preset TTS
curl -sS -X POST http://localhost:8787/v1/audio/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Nexus","speaker":"serena"}' \
  --output /tmp/nexus-tts.wav

# STT
curl -sS -X POST http://localhost:8787/v1/audio/transcribe \
  -F "audio=@/tmp/nexus-tts.wav"

# List recorded runs
curl -sS http://localhost:8787/v1/runs

# List submitted experiments
curl -sS http://localhost:8787/v1/experiments
```

### Accept the Gemma 4 license

Gemma 4 is a gated model, so you must accept the license before downloading or using it in training/evaluation workflows:
1. Go to https://huggingface.co/google/gemma-4-e2b
2. Click "Agree and access repository"
3. Make sure your `HF_TOKEN` in `.env` matches your HuggingFace account

---

## Your first experiment: SFT + LoRA

This runs in ~10 minutes on an M2 Mac with `max_samples: 1000`.

```bash
# Preview the dataset (no download required)
nexus data inspect --name tatsu-lab/alpaca

# Run SFT training (reads configs/recipes/sft_lora.yaml)
nexus train run --recipe configs/recipes/sft_lora.yaml

# Evaluate your trained model
nexus eval perplexity --checkpoint .data/checkpoints/gemma4-e2b-sft-lora

# Chat with your fine-tuned model through the API
curl -sS -X POST http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "HuggingFaceTB/SmolLM2-135M-Instruct",
    "messages": [{"role": "user", "content": "Explain why the sky is blue."}]
  }'
```

For a quick smoke test, set `max_samples: 1000` in `configs/recipes/sft_lora.yaml`
before running.

---

## All commands

```bash
# API
nexus api serve

# Training
nexus train run --recipe configs/recipes/sft_lora.yaml    # SFT + LoRA
nexus train run --recipe configs/recipes/dpo.yaml         # DPO
nexus train run --recipe configs/recipes/orpo.yaml        # ORPO
nexus train run --recipe configs/recipes/grpo.yaml        # GRPO
nexus train run --recipe my-recipe.yaml --no-wandb        # disable W&B

# Evaluation
nexus eval perplexity --checkpoint .data/checkpoints/my-run
nexus eval judge --checkpoint .data/checkpoints/my-run

# Experiments
nexus experiment run --phase 1
nexus experiment run --phase 2 --large-model MiniMax-M2.7
nexus experiment run --phase 3 --samples 50 --no-wandb

# Data
nexus data list                              # show recommended datasets
nexus data inspect --name tatsu-lab/alpaca  # preview without downloading
nexus data download --name tatsu-lab/alpaca # download and cache

```

---

## Project structure

```text
nexus/
├── compose.yml             # local runtime graph: API + text/audio workers
├── configs/
│   ├── models/             # model configs
│   ├── data/               # dataset configs
│   ├── recipes/            # training recipes
│   └── benchmarks/         # experiment presets
├── assets/                 # sample assets used in local workflows
├── docs/
│   ├── taxonomy/           # canonical platform nouns
│   ├── api-taxonomy.md     # route naming contract
│   └── storage-model.md    # durable storage contract
├── src/nexus/
│   ├── api/                # public control-plane app, routers, API models
│   ├── text/               # private text-generation worker service
│   ├── audio/              # private TTS / ASR worker service
│   ├── runs/               # canonical run schema + SQLite store
│   ├── experiments/        # benchmark schemas, runners, cache, store
│   ├── evaluation/         # evaluation schemas, metrics, store
│   ├── artifacts/          # artifact schemas (store not implemented yet)
│   ├── jobs/               # job schemas (store not implemented yet)
│   ├── cli/                # nexus api/train/eval/data/experiment commands
│   ├── data/               # dataset loading and formatting helpers
│   ├── models/             # model loading and adapter helpers
│   ├── trainers/           # SFT, DPO, ORPO, and GRPO trainers
│   ├── config.py           # training and benchmark config models
│   ├── device.py           # Apple Silicon / MPS detection
│   ├── runtime.py          # explicit runtime guards for Apple workflows
│   └── schemas/            # compatibility shims for canonical schemas
├── infra/                  # Dockerfiles and runtime assets
├── research/               # disposable labs and benchmark notes
├── .data/                  # ignored local runtime data and caches
└── tests/                  # pytest test suite
```

## Current State

Implemented and tested today:

- public API routes for text, audio, runs, and experiments
- canonical SQLite stores for runs, experiments, and evaluations
- text and audio backend worker apps
- local posttraining workflows for SFT, DPO, ORPO, and GRPO
- benchmark phases for baseline, open-book, and reflection experiments

Still in progress:

- exposing evaluations, jobs, artifacts, and benchmarks as public API resources
- adding durable stores for jobs and artifacts
- reducing legacy compatibility shims as the canonical noun model settles

See `docs/taxonomy/nexus.md` for platform boundaries and runtime topology.
See `docs/taxonomy/README.md` for the canonical noun model.
See `docs/api-taxonomy.md`, `docs/storage-model.md`, and `src/nexus/*/schema.py` for implementation contracts.

---

## Concepts glossary

**LoRA** — Low-Rank Adaptation. Instead of updating all model weights, LoRA inserts
small trainable matrices alongside specific layers. Only ~0.1% of parameters are trained.
This makes fine-tuning feasible on a Mac.

**SFT** — Supervised Fine-Tuning. Train the model to produce specific responses
given specific prompts. The simplest form of fine-tuning.

**DPO** — Direct Preference Optimization. Given (prompt, good response, bad response),
train the model to prefer good responses over bad ones. No reward model needed.

**ORPO** — Odds Ratio Preference Optimization. Combines SFT and preference learning
in a single training pass. More efficient than doing SFT then DPO separately.

**GRPO** — Group Relative Policy Optimization. Generates multiple responses per prompt,
scores them with a reward function, and updates the model to produce higher-scoring
responses. Used to train DeepSeek R1.

**Perplexity** — How surprised the model is by validation data. Lower = better.
exp(cross_entropy_loss). A perplexity of 10 means the model is as uncertain
as uniformly choosing from 10 options at each step.

**bfloat16** — 16-bit floating point format Gemma was trained with. Using float16
instead causes NaN gradients. Always use bfloat16.

**W&B** — Weights & Biases. A tool that logs your training metrics to a web dashboard
so you can compare runs, spot overfitting, and share results.

---

## Experiment tracking

Training metrics are logged to [Weights & Biases](https://wandb.ai) automatically.
After your first run, go to your W&B project to see:
- Training loss curve
- Validation loss curve
- Learning rate schedule
- Gradient norms
- DPO/ORPO: reward margins and accuracy

To disable W&B for a run: `nexus train run --recipe ... --no-wandb`

---

## Memory requirements

The Docker runtime is split across a small public API container and private
model workers. The text worker uses a standard HuggingFace transformers model,
and the audio workers each have their own dedicated image.

---

## Running tests

```bash
make test           # run all tests
make test-cov       # with coverage report
make lint           # check code style
make format         # auto-format
```

---

## Recommended learning path

1. **Read** `src/nexus/config.py` — understand the Recipe system
2. **Run** `nexus data inspect --name tatsu-lab/alpaca` — see what training data looks like
3. **Run** SFT with `max_samples: 1000` — watch the loss go down
4. **Read** `src/nexus/trainers/sft.py` — understand what's happening
5. **Compare** your fine-tuned model vs the base with the API `curl` flow
6. **Try** DPO — read `src/nexus/trainers/dpo.py` first
7. **Experiment** — modify hyperparameters, compare runs in W&B
8. **Build** a custom GRPO reward function for a task you care about
