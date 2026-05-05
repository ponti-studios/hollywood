UV := uv

.PHONY: setup setup-apple install train train-sft train-dpo train-orpo train-grpo \
        eval data-alpaca data-ultrafeedback \
	exp-baseline exp-baseline-quick exp-open-book exp-reflection \
	smoke-eval \
        test test-cov lint format typecheck clean help

# Default smoke-eval reference model.
SMOKE_MODEL   ?= Qwen/Qwen3.5-4B
SMOKE_SAMPLES ?= 25

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Install cross-platform dev dependencies (no Apple runtime stack)
	$(UV) pip install -e ".[dev,notebook]"

setup-apple: ## Install full Apple Silicon runtime (training + inference)
	$(UV) pip install -e ".[dev,notebook]"
	$(UV) pip install torch accelerate peft trl

install: ## Install Apple Silicon runtime dependencies only
	$(UV) pip install torch accelerate peft trl

# ── Training ──────────────────────────────────────────────────────────────────

# Usage:  make train RECIPE=configs/recipes/sft_lora.yaml
train: ## Run any training recipe  (RECIPE=path/to/recipe.yaml)
	$(UV) run nexus train --recipe $(RECIPE)

train-sft: ## SFT + LoRA on Gemma 4 E2B with Alpaca
	$(UV) run nexus train --recipe configs/recipes/sft_lora.yaml

train-dpo: ## DPO on Gemma 4 E2B with UltraFeedback
	$(UV) run nexus train --recipe configs/recipes/dpo.yaml

train-orpo: ## ORPO on Gemma 4 E2B
	$(UV) run nexus train --recipe configs/recipes/orpo.yaml

train-grpo: ## GRPO on Gemma 4 E2B
	$(UV) run nexus train --recipe configs/recipes/grpo.yaml

# ── Evaluation ────────────────────────────────────────────────────────────────

# Usage:  make eval CHECKPOINT=.data/checkpoints/my-run
eval: ## Evaluate a trained checkpoint
	$(UV) run nexus eval --checkpoint $(CHECKPOINT)

# ── Data ──────────────────────────────────────────────────────────────────────

data-alpaca: ## Download Alpaca dataset (classic SFT benchmark)
	$(UV) run nexus data download --name tatsu-lab/alpaca

data-ultrafeedback: ## Download UltraFeedback dataset (DPO / ORPO)
	$(UV) run nexus data download --name trl-lib/ultrafeedback_binarized

# ── Experiments ───────────────────────────────────────────────────────────────

exp-baseline: ## Phase 1 full baseline (500 samples, ~30 min on M-series)
	$(UV) run nexus experiment run --config configs/benchmarks/exp_01.yaml

exp-baseline-quick: ## Phase 1 quick sanity check (50 samples, no W&B, ~3 min)
	$(UV) run nexus experiment run --samples 50 --no-wandb

exp-open-book: ## Phase 2 open-book benchmark (500 samples, search-enabled)
	$(UV) run nexus experiment run --config configs/benchmarks/exp_02.yaml

exp-reflection: ## Phase 3 reflection benchmark (500 samples, draft/critique/refine)
	$(UV) run nexus experiment run --config configs/benchmarks/exp_03.yaml

smoke-eval: ## Live 3-phase smoke eval against Qwen (25 samples, no W&B)
	@echo "=== Phase 1: closed-book baseline ==="
	$(UV) run nexus experiment run --phase 1 --samples $(SMOKE_SAMPLES) \
		--large-model $(SMOKE_MODEL) --no-wandb
	@echo "=== Phase 2: open-book (tool use) ==="
	$(UV) run nexus experiment run --phase 2 --samples $(SMOKE_SAMPLES) \
		--large-model $(SMOKE_MODEL) --no-wandb
	@echo "=== Phase 3: reflection (draft/critique/refine) ==="
	$(UV) run nexus experiment run --phase 3 --samples $(SMOKE_SAMPLES) \
		--large-model $(SMOKE_MODEL) --no-wandb
	@echo "=== Smoke eval complete. Review .data/benchmarks/cache/ for outputs. ==="

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
