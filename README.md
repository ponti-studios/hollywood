# nexus — Multimodal Inference, Training, and Evaluation Platform

Nexus is the control plane for multimodal generative systems.

Today, the repo contains three closely related layers:

- a public FastAPI control plane for text, audio, runs, and experiments
- private text and audio worker services behind that API
- local training, evaluation, and benchmark workflows for posttraining experiments

The canonical product language, API naming, storage model, and implementation contracts live in this README.

## Nexus taxonomy

This is the canonical noun model, API taxonomy, storage taxonomy, and naming alignment for Nexus.

Use these nouns consistently for package names, API routes, storage tables,
job types, UI labels, and internal services.

### Canonical nouns

| Noun | Meaning | Implemented | Planned |
| --- | --- | --- | --- |
| Nexus | the platform / control plane | `nexus` package, `nexus api serve`, root `compose.yml` service, `/health`, `/v1/*` | stay the stable platform noun |
| Capability | a product domain such as audio or text | `audio` under `src/nexus/audio/` with `/v1/audio/*` routes | add `text`, `image`, and other bounded contexts |
| Model | an asset the platform operates on | model loading in `src/nexus/models/`, identity tracked by string ID | durable model registry with stable IDs |
| Inference | producing outputs from a model | `/v1/chat/completions`, audio TTS/STT flows, durable run records | more inference surfaces and modalities |
| Training | updating model parameters or adapters | `src/nexus/trainers/`, YAML recipes, `src/nexus/cli/train.py` | durable run/artifact records and eventual rename to `training` |
| Evaluation | measuring quality for a subject | `src/nexus/evaluation/` schema + store, linked to runs and experiments | more subjects and scorers |
| Benchmark | defining a reusable test | benchmark logic in `src/nexus/experiments/benchmarks/` with `configs/benchmarks/` | stable IDs and a first-class store |
| Experiment | comparing variants under a hypothesis | `src/nexus/experiments/` schema + store, linked evaluation IDs, summary scores | reuse the same comparison record for new workflows |
| Run | recording a single execution | `src/nexus/runs/` durable SQLite store, inference runs already recorded | benchmark trials and evaluation passes also write here |
| Job | orchestrating lifecycle-managed work | `src/nexus/jobs/schema.py` | durable store for queueing, retries, cancellation, progress |
| Artifact | persisting durable output | `src/nexus/artifacts/schema.py` | durable store for stable artifact records |

### API taxonomy

Platform primitives live at `/v1/{noun}`. Capability-specific actions live at `/v1/{capability}/{action}`.

| Route | Status | Notes |
| --- | --- | --- |
| `GET /health` | implemented | health check |
| `GET /v1/runs`, `GET /v1/runs/{id}`, `DELETE /v1/runs/{id}` | implemented | run ledger |
| `GET /v1/experiments`, `POST /v1/experiments`, `GET /v1/experiments/{experiment_id}`, `GET /v1/experiments/{experiment_id}/results` | implemented | experiment workflows |
| `GET /v1/audio/health`, `POST /v1/audio/tts`, `POST /v1/audio/transcribe` | implemented | audio capability routes |
| `POST /v1/chat/completions` | implemented | text inference |
| `/v1/evaluations` | planned | platform resource |
| `/v1/jobs` | planned | platform resource |
| `/v1/artifacts` | planned | platform resource |
| `/v1/benchmarks` | planned | platform resource |

Rules:

- use nouns, not verbs, for resources
- capability routes own modality-specific payloads
- platform routes stay stable across capabilities
- do not encode implementation detail into routes

### Storage taxonomy

Nexus keeps durable platform records in a shared SQLite database at `.data/api/inference.db`.

| Store | Status | Notes |
| --- | --- | --- |
| `runs` | implemented | atomic execution records for inference and other workflows |
| `experiments` | implemented | comparison records with status, config snapshot, scores, and evaluation linkage |
| `evaluations` | implemented | quality measurement records linked to runs, experiments, and benchmarks |
| `jobs` | planned | schema exists, store does not yet exist |
| `artifacts` | planned | schema exists, store does not yet exist |
| `models` | planned | schema exists, store does not yet exist |

Keep these storage kinds separate:

- platform records are durable, queryable, and keyed by stable IDs
- capability files and caches are modality-specific outputs that live in `.data/audio/`, `assets/audio/`, benchmark cache dirs, and similar locations
- research outputs in `research/` are exploratory and disposable

A file on disk is not a platform record. A generated wav file is a file. An artifact record with a URI pointing to that file is a platform record.

### Naming alignment

Current package alignment:

- platform — `nexus`
- audio capability — `src/nexus/audio`
- API control plane — `src/nexus/api`
- run records — `src/nexus/runs`
- evaluation — `src/nexus/evaluation`
- experiments — `src/nexus/experiments`
- jobs — `src/nexus/jobs` schema only
- artifacts — `src/nexus/artifacts` schema only
- training workflows — `src/nexus/trainers`

Open naming gap:

- `src/nexus/trainers` should eventually become `src/nexus/training`
- the taxonomy noun is `training`; `trainers` is an implementation detail

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
- Python 3.12.x for the training stack
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

# Runtime install: API server, CLI tools, datasets, and formatting helpers
mise exec -- uv venv .venv
uv pip install -e ".[runtime]"

# Training / evaluation install: adds torch, PEFT, and TRL
uv pip install -e ".[train]"

# Full contributor install: runtime + training + test tooling
uv pip install -e ".[dev]"

# Optional notebooks and exploratory analysis
uv pip install -e ".[notebook]"

# Or install everything in one shot
uv pip install -e ".[all]"

# Or use the just targets
just setup
just setup-runtime
just setup-train
just setup-notebook
just setup-all
just install-cli

# Copy and fill in your API keys
cp .env.example .env
# Edit .env: add HF_TOKEN and WANDB_API_KEY
```

`just setup` installs the full contributor environment. `just setup-runtime`
installs the API / CLI bundle, `just setup-train` installs the training and
evaluation bundle, and `just setup-notebook` / `just setup-all` cover the
analysis and everything-everywhere cases. Training and perplexity evaluation
still require macOS on Apple Silicon, and the CLI now guards those commands so
they fail early if Python, platform, or optional runtime dependencies are wrong.

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
    "model": "google/gemma-4-E2B-it",
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
1. Go to https://huggingface.co/google/gemma-4-E2B-it
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
nexus eval perplexity --checkpoint .data/checkpoints/gemma4-e2b-it-sft-lora

# Chat with your fine-tuned model through the API
curl -sS -X POST http://localhost:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-4-E2B-it",
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
nexus experiment run --phase 2
nexus experiment run --phase 3

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
│   ├── recipes/            # training recipes
│   └── benchmarks/         # experiment presets
├── assets/                 # sample assets used in local workflows
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
│   ├── runtime.py          # explicit runtime guards for training workflows
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

See the Nexus taxonomy and naming alignment sections above for the canonical noun model, platform boundaries, API routes, and storage model.
See `src/nexus/*/schema.py` for package-owned schemas.

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
just test           # run all tests
just test-cov       # with coverage report
just lint           # check code style
just format         # auto-format
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
