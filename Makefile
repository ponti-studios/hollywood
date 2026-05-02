UV := uv

.PHONY: setup setup-apple install train train-sft train-dpo train-orpo train-grpo \
        eval serve-1b serve-4b data-alpaca data-ultrafeedback \
	exp-baseline exp-baseline-quick exp-open-book exp-reflection \
	smoke-eval \
        test test-cov test-inference test-inference-quick lint format typecheck clean help

# MINIMAX_API_KEY must be set in env before running smoke-eval
SMOKE_MODEL   ?= MiniMax-M2.7
SMOKE_SAMPLES ?= 25

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Install cross-platform dev dependencies (no Apple runtime stack)
	$(UV) pip install -e ".[dev,notebook]"

setup-apple: ## Install full Apple Silicon runtime (training + inference)
	$(UV) pip install -e ".[dev,notebook]"
	$(UV) pip install torch accelerate peft trl mlx mlx-lm mlx-vlm

setup-mlx: ## Install MLX inference-only stack (no PyTorch; Gemma 4 E2B + tool calling)
	$(UV) pip install -e ".[dev,notebook]"
	$(UV) pip install mlx mlx-lm mlx-vlm

install: ## Install Apple Silicon runtime dependencies only
	$(UV) pip install torch accelerate peft trl mlx mlx-lm mlx-vlm

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

# ── Serving ───────────────────────────────────────────────────────────────────────
# Note: Both serve-1b and serve-4b use the same MLX-VLM Gemma 4 E2B model.
# Consider renaming these targets if different models are added in the future.

serve-1b: ## Serve Gemma 4 E2B locally via MLX-VLM (first run: downloads ~10GB)
	$(UV) run nexus serve run --model mlx-community/gemma-4-e2b-bf16

serve-4b: ## Serve Gemma 4 E2B locally via MLX-VLM (first run: downloads ~10GB)
	$(UV) run nexus serve run --model mlx-community/gemma-4-e2b-bf16

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

smoke-eval: ## Live 3-phase smoke eval against MiniMax (25 samples, no W&B)
	@if [ -z "$$MINIMAX_API_KEY" ]; then \
		echo "ERROR: MINIMAX_API_KEY is not set. Export it before running smoke-eval."; \
		exit 1; \
	fi
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

test-inference: ## Run all 9 Gemma 4 inference tests (requires MLX stack + model download)
	@./scripts/run_inference_tests.sh

test-inference-quick: ## Run single quick inference test (smoke test)
	@./scripts/run_inference_tests.sh --quick

test-inference-verbose: ## Run all inference tests with verbose output
	@./scripts/run_inference_tests.sh --verbose

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
