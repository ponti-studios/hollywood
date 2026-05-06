"""
grpo.py — Group Relative Policy Optimization (GRPO) trainer.

What is GRPO?
─────────────
GRPO (DeepSeek-AI, 2024) is the algorithm used to train DeepSeek R1, the
reasoning model that shocked the ML world in early 2025.

It's a variant of PPO (Proximal Policy Optimization) that is much more
memory-efficient because it removes the need for a separate value model.

How GRPO works:
  1. For each prompt, generate a GROUP of N responses (e.g. N=8)
  2. Score each response with a REWARD FUNCTION you define
  3. Use the group to estimate a relative "advantage" for each response:
       advantage_i = (reward_i − mean(rewards)) / std(rewards)
  4. Update the model to increase probability of high-advantage responses

The key insight: instead of training a value function (expensive),
GRPO uses the group average reward as the baseline. Simpler and cheaper.

Why is this exciting?
─────────────────────
The reward function can be ANYTHING. For reasoning tasks you can reward:
  - Correct final answers (easy to check automatically)
  - Valid format (e.g. always wrap reasoning in <think> tags)
  - Length (reward conciseness or thoroughness)

This means you can train the model to reason better WITHOUT human labels —
just check if the answer is correct. This is called "self-play" or
"outcome-based reward modelling".

Data format:
  Each example needs a "prompt". You define a Python reward function that
  takes (prompt, response) and returns a float score.

Example reward function:
  def reward_correct_answer(responses, answers):
      return [1.0 if a.strip() in r else 0.0
              for r, a in zip(responses, answers)]
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

from trl import GRPOConfig, GRPOTrainer

from nexus.config import Recipe
from nexus.data.formatters import prepare_grpo_dataset
from nexus.data.loaders import load_and_split
from nexus.models.adapters import apply_lora, merge_and_save
from nexus.models.loader import load_model, load_tokenizer
from nexus.models.policy import write_model_manifest

logger = logging.getLogger(__name__)

# Type alias for a reward function
# A reward function receives a list of responses (strings) and returns a list of scores
RewardFn = Callable[[list[str]], list[float]]


def default_length_reward(responses: list[str]) -> list[float]:
    """A trivial reward function that rewards longer responses.

    This is just a demo — replace it with something meaningful for your task.
    For example, a math reward function would parse the answer and check correctness.
    """
    return [min(len(r) / 500, 1.0) for r in responses]


def format_compliance_reward(responses: list[str]) -> list[float]:
    """Reward responses that contain a reasoning step in <think> tags.

    This is the reward function style used by DeepSeek R1 to encourage
    the model to show its reasoning before giving the final answer.
    """
    scores = []
    for response in responses:
        has_think = bool(re.search(r"<think>.*?</think>", response, re.DOTALL))
        scores.append(1.0 if has_think else 0.0)
    return scores


def run_grpo(
    recipe: Recipe,
    reward_fn: RewardFn | None = None,
) -> None:
    """Run a full GRPO training run from a Recipe.

    Args:
        recipe:    a fully validated Recipe loaded from a YAML config
        reward_fn: your reward function. Receives a list of generated responses,
                   returns a list of float scores (higher = better).
                   Defaults to a simple length-based reward for demonstration.
    """
    logger.info(f"Starting GRPO run: {recipe.name}")

    if reward_fn is None:
        logger.warning(
            "No reward function provided — using default length reward. "
            "For real experiments, define a meaningful reward function."
        )
        reward_fn = default_length_reward

    # ── 1. Load tokenizer + model ─────────────────────────────────────────
    tokenizer = load_tokenizer(recipe.model)
    model = load_model(recipe.model)

    # ── 2. Apply LoRA ─────────────────────────────────────────────────────
    if recipe.lora is not None:
        model = apply_lora(model, recipe.lora)

    # ── 3. Load dataset ────────────────────────────────────────────────────
    splits = load_and_split(recipe.data)
    train_dataset = prepare_grpo_dataset(splits["train"])
    eval_dataset = prepare_grpo_dataset(splits["validation"])

    # ── 4. Configure GRPO ─────────────────────────────────────────────────
    t = recipe.training
    output_dir = str(recipe.resolve_output_dir())

    grpo_config = GRPOConfig(
        output_dir=output_dir,
        num_train_epochs=t.num_epochs,
        per_device_train_batch_size=t.batch_size,
        per_device_eval_batch_size=t.batch_size,
        gradient_accumulation_steps=t.gradient_accumulation_steps,
        learning_rate=t.learning_rate,
        weight_decay=t.weight_decay,
        warmup_ratio=t.warmup_ratio,
        lr_scheduler_type="cosine",
        max_grad_norm=t.max_grad_norm,
        bf16=t.bf16,
        fp16=False,
        logging_steps=t.logging_steps,
        eval_strategy="steps",
        eval_steps=t.eval_steps,
        save_strategy="steps",
        save_steps=t.save_steps,
        save_total_limit=3,
        report_to="wandb" if recipe.wandb.enabled else "none",
        run_name=recipe.wandb.run_name or recipe.name,
        optim="adamw_torch",
        dataloader_pin_memory=False,
        seed=recipe.data.seed,
        # GRPO-specific
        num_generations=4,  # N responses to generate per prompt per step
        # More = better gradient estimate but more memory
        # 4 is a good starting point on Apple Silicon
        max_completion_length=256,  # max tokens to generate per response
        temperature=0.9,  # sampling temperature for generation
        beta=0.04,  # KL penalty to prevent collapsing to degenerate responses
    )

    # ── 5. Train ───────────────────────────────────────────────────────────
    trainer = GRPOTrainer(
        model=model,
        args=grpo_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        reward_funcs=[reward_fn],  # TRL accepts a list of reward functions
    )

    logger.info("Training …")
    trainer.train()

    if recipe.lora is not None:
        merge_and_save(model, tokenizer, output_dir)
    else:
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)
        write_model_manifest(output_dir)

    logger.info(f"Model saved to {output_dir}")
