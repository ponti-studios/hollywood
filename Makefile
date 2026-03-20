UV := uv

.PHONY: setup setup-apple install train train-sft train-dpo train-orpo train-grpo \
        eval serve-1b serve-4b data-alpaca data-ultrafeedback \
        exp-baseline exp-baseline-quick \
        test test-cov lint format typecheck clean help

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Install cross-platform dev dependencies (no Apple runtime stack)
	$(UV) pip install -e ".[dev,notebook]"

setup-apple: ## Install Apple Silicon runtime (recreate venv as arm64 first if needed)
	$(UV) pip install -e ".[dev,notebook]"
	$(UV) pip install torch accelerate peft trl mlx mlx-lm

setup-mlx: ## Install MLX inference-only stack (no PyTorch, faster install)
	$(UV) pip install -e ".[dev,notebook]"
	$(UV) pip install mlx mlx-lm

install: ## Install Apple Silicon runtime dependencies only
	$(UV) pip install torch accelerate peft trl mlx mlx-lm

# ── Training ──────────────────────────────────────────────────────────────────

# Usage:  make train RECIPE=configs/recipes/sft_lora.yaml
train: ## Run any training recipe  (RECIPE=path/to/recipe.yaml)
	$(UV) run nexus train --recipe $(RECIPE)

train-sft: ## SFT + LoRA on Gemma 3 1B with Alpaca
	$(UV) run nexus train --recipe configs/recipes/sft_lora.yaml

train-dpo: ## DPO on Gemma 3 1B with UltraFeedback
	$(UV) run nexus train --recipe configs/recipes/dpo.yaml

train-orpo: ## ORPO on Gemma 3 1B
	$(UV) run nexus train --recipe configs/recipes/orpo.yaml

train-grpo: ## GRPO on Gemma 3 1B
	$(UV) run nexus train --recipe configs/recipes/grpo.yaml

# ── Evaluation ────────────────────────────────────────────────────────────────

# Usage:  make eval CHECKPOINT=experiments/my-run
eval: ## Evaluate a trained checkpoint
	$(UV) run nexus eval --checkpoint $(CHECKPOINT)

# ── Serving ───────────────────────────────────────────────────────────────────

serve-1b: ## Serve Gemma 3 1B locally via MLX (fast Apple Silicon path)
	$(UV) run nexus serve --model google/gemma-3-1b-it

serve-4b: ## Serve Gemma 3 4B locally via MLX
	$(UV) run nexus serve --model google/gemma-3-4b-it

# ── Data ──────────────────────────────────────────────────────────────────────

data-alpaca: ## Download Alpaca dataset (classic SFT benchmark)
	$(UV) run nexus data download --name tatsu-lab/alpaca

data-ultrafeedback: ## Download UltraFeedback dataset (DPO / ORPO)
	$(UV) run nexus data download --name trl-lib/ultrafeedback_binarized

# ── Experiments ───────────────────────────────────────────────────────────────

exp-baseline: ## Phase 1 full baseline (500 samples, ~30 min on M-series)
	$(UV) run nexus experiment run --config experiments/configs/exp_01.yaml

exp-baseline-quick: ## Phase 1 quick sanity check (50 samples, no W&B, ~3 min)
	$(UV) run nexus experiment run --samples 50 --no-wandb

# ── Development ───────────────────────────────────────────────────────────────

test: ## Run the test suite
	$(UV) run pytest

test-cov: ## Run tests with coverage report
	$(UV) run pytest --cov=nexus --cov-report=term-missing

lint: ## Check code style
	$(UV) run ruff check src/ tests/

format: ## Auto-format code
	$(UV) run ruff format src/ tests/
	$(UV) run ruff check --fix src/ tests/

typecheck: ## Run static type checker
	$(UV) run pyright src/

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache dist/ .ruff_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
