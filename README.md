# nexus — Gemma 3 Posttraining Lab

A hands-on lab for learning posttraining techniques on Apple Silicon.
Experiments with Gemma 3 1B and 4B using SFT, DPO, ORPO, and GRPO.

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

# Full Apple Silicon runtime install: training, eval, serving
uv pip install -e ".[dev,notebook,apple]"

# Or use the Makefile shortcuts
make setup
make setup-apple

# Copy and fill in your API keys
cp .env.example .env
# Edit .env: add HF_TOKEN and WANDB_API_KEY
```

`make setup` is intentionally cross-platform and does not install the Apple-only
runtime stack. Training, perplexity evaluation, and MLX serving require the
`apple` extra on Apple Silicon, and the CLI now guards those commands so they
fail early if Python, platform, or optional runtime dependencies are wrong.

### Accept the Gemma 3 license

Gemma 3 is a gated model. You must accept the license before downloading:
1. Go to https://huggingface.co/google/gemma-3-1b-it
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
nexus eval perplexity --checkpoint .data/checkpoints/gemma3-1b-sft-lora

# Chat with your fine-tuned model
nexus serve chat --model .data/checkpoints/gemma3-1b-sft-lora
```

For a quick smoke test, set `max_samples: 1000` in `configs/recipes/sft_lora.yaml`
before running.

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

# Serving (Apple Silicon / MLX — fastest)
nexus serve chat --model google/gemma-3-1b-it            # interactive chat
nexus serve run  --model google/gemma-3-1b-it --port 8080 # HTTP server
```

---

## Project structure

```
nexus/
├── configs/
│   ├── models/           # gemma3-1b.yaml, gemma3-4b.yaml
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
│   │   ├── loader.py     # load Gemma 3 with bf16, MPS placement
│   │   └── adapters.py   # LoRA: apply, merge, save, load
│   ├── trainers/
│   │   ├── sft.py        # Supervised Fine-Tuning
│   │   ├── dpo.py        # Direct Preference Optimization
│   │   ├── orpo.py       # Odds Ratio Preference Optimization
│   │   └── grpo.py       # Group Relative Policy Optimization
│   ├── evaluation/
│   │   ├── metrics.py    # perplexity, token accuracy
│   │   └── judge.py      # LLM-as-judge scoring via MLX
│   └── cli/
│       ├── train.py      # nexus train
│       ├── eval.py       # nexus eval
│       ├── data.py       # nexus data
│       └── serve.py      # nexus serve
│
├── apps/                 # runnable applications and service entrypoints
├── research/             # model bake-offs and disposable labs
├── infra/                # Dockerfiles, Compose, and operational assets
├── .data/                # ignored local runtime data and caches
└── tests/                # pytest test suite
```

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

**bfloat16** — 16-bit floating point format Gemma 3 was trained with. Using float16
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

| Model | Precision | Weights | + LoRA training |
|-------|-----------|---------|----------------|
| Gemma 3 1B | bfloat16 | ~2 GB | ~4 GB total |
| Gemma 3 4B | bfloat16 | ~8 GB | ~12 GB total |
| Gemma 3 1B | 4-bit (MLX) | ~0.5 GB | inference only |
| Gemma 3 4B | 4-bit (MLX) | ~2 GB | inference only |

For inference/serving, use the 4-bit quantised MLX models from
`mlx-community/gemma-3-1b-it-4bit` — they're 4× smaller with minimal quality loss.

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
5. **Compare** your fine-tuned model vs the base with `nexus serve chat`
6. **Try** DPO — read `src/nexus/trainers/dpo.py` first
7. **Experiment** — modify hyperparameters, compare runs in W&B
8. **Build** a custom GRPO reward function for a task you care about
