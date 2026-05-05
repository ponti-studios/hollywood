# nexus — Multimodal Inference, Training, and Evaluation Platform

Nexus is the studio control plane for multimodal generative systems.

For the **canonical definition of Nexus**, see:
- `docs/taxonomy/nexus.md`

For the canonical noun model and implementation contracts, see:
- `docs/taxonomy/README.md`
- `docs/api-taxonomy.md`
- `docs/storage-model.md`
- `src/nexus/*/schema.py`

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
- Python 3.12.5 for the Apple runtime stack
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

---

## All commands

```bash
# Training
nexus train run --recipe configs/recipes/sft_lora.yaml    # SFT + LoRA
nexus train run --recipe configs/recipes/dpo.yaml         # DPO
nexus train run --recipe configs/recipes/orpo.yaml        # ORPO
nexus train run --recipe configs/recipes/grpo.yaml        # GRPO
nexus train run --recipe my-recipe.yaml --no-wandb        # disable W&B

# Evaluation
nexus eval perplexity --checkpoint .data/checkpoints/my-run
nexus eval judge --checkpoint .data/checkpoints/my-run

# Data
nexus data list                              # show recommended datasets
nexus data inspect --name tatsu-lab/alpaca  # preview without downloading
nexus data download --name tatsu-lab/alpaca # download and cache

```

---

## Project structure

```
nexus/
├── configs/
│   ├── models/           # Gemma model configs
│   ├── data/             # alpaca.yaml, ultrafeedback.yaml
│   ├── recipes/          # sft_lora.yaml, dpo.yaml, orpo.yaml, grpo.yaml
│   └── benchmarks/       # exp_01.yaml, exp_02.yaml, exp_03.yaml
│
├── assets/               # example/sample artifacts used for local workflows
├── src/nexus/
│   ├── config.py         # Pydantic config models (Recipe, ModelConfig, …)
│   ├── device.py         # Apple Silicon / MPS detection
│   ├── data/
│   │   ├── loaders.py    # HuggingFace dataset loading + train/val split
│   │   └── formatters.py # chat templates, SFT/DPO/GRPO data formatting
│   ├── models/
│   │   ├── loader.py     # load Gemma with bf16, MPS placement
│   │   └── adapters.py   # LoRA: apply, merge, save, load
│   ├── trainers/
│   │   ├── sft.py        # Supervised Fine-Tuning
│   │   ├── dpo.py        # Direct Preference Optimization
│   │   ├── orpo.py       # Odds Ratio Preference Optimization
│   │   └── grpo.py       # Group Relative Policy Optimization
│   ├── evaluation/
│   │   ├── metrics.py    # perplexity, token accuracy
│   │   └── judge.py      # LLM-as-judge scoring
│   └── cli/
│       ├── train.py      # nexus train
│       ├── eval.py       # nexus eval
│       ├── data.py       # nexus data
│       └── api.py        # nexus api
│
├── apps/                 # legacy app entrypoints; being folded into src/nexus/api
├── research/             # model bake-offs and disposable labs
├── infra/                # Dockerfiles, Compose, and operational assets
├── .data/                # ignored local runtime data and caches
└── tests/                # pytest test suite
```

See `docs/taxonomy/nexus.md` for the current Nexus platform boundaries and runtime topology.
See `docs/taxonomy/README.md` for the canonical Nexus noun model.
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
