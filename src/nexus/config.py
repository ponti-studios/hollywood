"""
config.py — Typed configuration models for every training recipe.

Why Pydantic?
─────────────
Pydantic validates your YAML config at load time and gives you a clear error
message if something is wrong (wrong type, missing field, invalid value).
Without this you'd get cryptic crashes deep inside the training loop.

How configs work in this repo:
  1. You write a YAML file (e.g. configs/recipes/sft_lora.yaml)
  2. Recipe.from_yaml("configs/recipes/sft_lora.yaml") loads + validates it
  3. The resulting Recipe object is passed to a Trainer

Every field has a sensible default so you only need to specify what you want
to change from the baseline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    """Which model to load and how to load it.

    model_id: the HuggingFace repo name, e.g. "google/gemma-3-1b-it"
              "-it" means "instruction-tuned" — the model already knows how
              to follow instructions, which is a much better starting point
              for posttraining than the raw base model.

    dtype: the numerical precision for weights.
           "bfloat16" is strongly recommended for Gemma 3 — it was trained
           in bfloat16 and using float16 can cause NaN (Not-a-Number) gradients.

    max_seq_len: maximum number of tokens in a single training example.
                 Longer = more context but more memory. 2048 is a good start.

    attn_implementation: "eager" is the safe default on Apple Silicon.
                         "flash_attention_2" is faster but requires CUDA.
    """

    model_id: str
    dtype: Literal["bfloat16", "float32"] = "bfloat16"
    max_seq_len: int = 2048
    attn_implementation: str = "eager"


class LoraConfig(BaseModel):
    """LoRA (Low-Rank Adaptation) configuration.

    LoRA is a Parameter-Efficient Fine-Tuning (PEFT) technique. Instead of
    updating all ~1-4 billion weights, LoRA inserts small "adapter" matrices
    next to specific weight matrices. Only the adapters are trained.

    Why LoRA?
    - Gemma 3 1B has ~1 billion parameters. Training all of them requires
      huge GPU memory and takes a long time.
    - With LoRA rank=16, you only train ~1-5 million extra parameters (~0.1%).
    - The final model quality is surprisingly close to full fine-tuning.

    rank (r): controls adapter size. Higher = more expressive but more memory.
              Common values: 8, 16, 32, 64. Start with 16.

    alpha: scaling factor for the LoRA updates. Usually set to 2 × rank.
           alpha/rank is the actual scale applied, so alpha=32, rank=16 → scale=2.

    dropout: randomly zeros adapter weights during training to prevent
             overfitting (memorising training data instead of learning).

    target_modules: which weight matrices inside each transformer layer to
                    apply LoRA to. These are the attention projection matrices.
                    q=query, k=key, v=value, o=output — all part of self-attention.
    """

    rank: int = Field(16, alias="r")
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list[str] = ["q_proj", "k_proj", "v_proj", "o_proj"]
    bias: Literal["none", "all", "lora_only"] = "none"

    model_config = {"populate_by_name": True}

    @field_validator("rank")
    @classmethod
    def rank_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("LoRA rank must be > 0")
        return v


class DataConfig(BaseModel):
    """Which dataset to load and how to preprocess it.

    dataset_name: HuggingFace dataset repo, e.g. "tatsu-lab/alpaca"
                  You can browse datasets at huggingface.co/datasets

    split: which split to use. Most datasets have "train" and "test".

    val_split: fraction of training data to hold out for validation.
               0.05 = 5% used to monitor if the model is overfitting.

    max_samples: cap on how many examples to use. None = use all.
                 Useful for quick experiments: set to 1000 for a fast run.

    seed: random seed for reproducibility. Same seed = same data shuffle.
    """

    dataset_name: str
    split: str = "train"
    val_split: float = 0.05
    max_samples: Optional[int] = None
    seed: int = 42
    text_column: str = "text"          # column name containing the text/messages
    prompt_column: str = "prompt"      # for DPO/ORPO: column with the prompt
    chosen_column: str = "chosen"      # for DPO/ORPO: preferred response
    rejected_column: str = "rejected"  # for DPO/ORPO: dispreferred response


class TrainingConfig(BaseModel):
    """Hyperparameters that control how training proceeds.

    method: which posttraining algorithm to use.
      - "sft":   Supervised Fine-Tuning — learn from (prompt, response) pairs.
                 The simplest and most common form of fine-tuning.
      - "dpo":   Direct Preference Optimization — learn which responses are
                 better given (prompt, chosen, rejected) triples. No reward model needed.
      - "orpo":  Odds Ratio Preference Optimization — combines SFT and preference
                 tuning in a single pass. Simpler than DPO.
      - "simpo": Simple Preference Optimization — like DPO but without needing
                 a reference model, which saves memory.
      - "grpo":  Group Relative Policy Optimization — used to train reasoning
                 models (like DeepSeek R1). Learns from a reward function.

    learning_rate: how large each gradient update step is.
                   Too high → unstable training. Too low → very slow.
                   2e-4 (= 0.0002) is a typical LoRA learning rate.

    num_epochs: how many times to iterate over the full dataset.
                More epochs → more training but risk of overfitting.

    batch_size: how many examples to process at once.
                Larger batches are more stable but use more memory.
                On Apple Silicon, 1-4 is typical.

    gradient_accumulation_steps: a trick to simulate a larger batch size.
                Accumulate gradients over N steps before updating weights.
                Effective batch size = batch_size × gradient_accumulation_steps.

    warmup_ratio: fraction of training steps where the learning rate slowly
                  ramps up from 0. Prevents unstable updates at the start.

    output_dir: where to save checkpoints. {name} is replaced with the recipe name.
    """

    method: Literal["sft", "dpo", "orpo", "simpo", "grpo"]
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 2
    gradient_accumulation_steps: int = 8
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    output_dir: str = "experiments/{name}"
    save_steps: int = 100
    logging_steps: int = 10
    eval_steps: int = 100
    max_grad_norm: float = 1.0         # clips gradients to prevent exploding updates
    bf16: bool = True                  # use bfloat16 for training (required for Gemma 3)
    fp16: bool = False                 # do NOT use float16 with Gemma 3

    @field_validator("fp16")
    @classmethod
    def fp16_and_bf16_conflict(cls, v: bool, info: object) -> bool:
        # fp16 can cause NaN gradients with Gemma 3 — always use bf16
        return False


class WandbConfig(BaseModel):
    """Weights & Biases experiment tracking configuration.

    W&B logs your training metrics (loss, learning rate, etc.) and lets you
    compare runs side-by-side in a browser dashboard. Free for personal use.

    enabled: set to False to disable tracking (or set WANDB_DISABLED=true in .env)
    project: the W&B project name (groups related experiments together)
    tags: free-form labels to help you filter runs later
    """

    enabled: bool = True
    project: str = "nexus-posttraining"
    run_name: Optional[str] = None     # auto-generated from recipe name if None
    tags: list[str] = []
    notes: str = ""


class Recipe(BaseModel):
    """A complete training experiment definition.

    A Recipe ties together a model, dataset, training algorithm, and tracking
    config. It maps 1:1 to a YAML file in configs/recipes/.

    Example usage:
        recipe = Recipe.from_yaml("configs/recipes/sft_lora.yaml")
        trainer = SFTTrainer(recipe)
        trainer.train()
    """

    name: str
    description: str = ""
    model: ModelConfig
    data: DataConfig
    training: TrainingConfig
    lora: Optional[LoraConfig] = None  # None = full fine-tuning (not recommended on Mac)
    wandb: WandbConfig = Field(default_factory=WandbConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Recipe":
        """Load and validate a recipe from a YAML file."""
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls(**raw)

    def resolve_output_dir(self) -> Path:
        """Replace {name} placeholder in output_dir with the actual recipe name."""
        return Path(self.training.output_dir.format(name=self.name))
