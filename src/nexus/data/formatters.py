"""
formatters.py — Apply chat templates and format datasets for each trainer type.

What is a "chat template"?
──────────────────────────
Language models are trained on text that follows a specific format to distinguish
between the human turn and the AI turn. For Gemma 3 this looks like:

    <start_of_turn>user
    What is the capital of France?<end_of_turn>
    <start_of_turn>model
    The capital of France is Paris.<end_of_turn>

The tokenizer knows this format (it's stored in tokenizer_config.json on HuggingFace).
We use `tokenizer.apply_chat_template()` so we never have to hardcode the format.

Different training methods expect different data formats
────────────────────────────────────────────────────────
  SFT:   {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
  DPO:   {"prompt": "...", "chosen": "...", "rejected": "..."}
  ORPO:  same as DPO — both the prompt and a pair of (chosen, rejected) responses
  GRPO:  {"prompt": "...", "answer": "..."}  — answer used to compute reward

Each function below transforms a raw HuggingFace dataset row into the
format expected by the corresponding TRL trainer.
"""

from __future__ import annotations

from typing import Any

from datasets import Dataset
from transformers import PreTrainedTokenizer


# ── SFT formatting ────────────────────────────────────────────────────────────

def format_alpaca_for_sft(example: dict[str, Any]) -> dict[str, Any]:
    """Convert an Alpaca-style row into the chat message format for SFTTrainer.

    The Alpaca dataset has columns: instruction, input (optional), output.
    We combine them into a two-turn conversation (user / assistant).
    """
    if example.get("input"):
        user_content = f"{example['instruction']}\n\n{example['input']}"
    else:
        user_content = example["instruction"]

    return {
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": example["output"]},
        ]
    }


def apply_chat_template_for_sft(
    example: dict[str, Any],
    tokenizer: PreTrainedTokenizer,
) -> dict[str, Any]:
    """Apply the tokenizer's chat template to a messages-formatted example.

    This converts the list of messages into a single string with the correct
    special tokens (e.g. <start_of_turn>user … <end_of_turn>).

    The `tokenize=False` means we return the formatted string, not token IDs.
    The actual tokenisation happens inside the TRL trainer's data collator.
    """
    return {
        "text": tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,  # don't add the trailing model turn opener
        )
    }


def prepare_sft_dataset(
    dataset: Dataset,
    tokenizer: PreTrainedTokenizer,
    dataset_name: str = "",
) -> Dataset:
    """Full pipeline: raw dataset → formatted strings ready for SFTTrainer.

    Dispatches to the right column-mapping function based on the dataset name,
    then applies the chat template.
    """
    # Step 1: reshape columns into the {"messages": [...]} format
    if "alpaca" in dataset_name.lower():
        dataset = dataset.map(format_alpaca_for_sft, remove_columns=dataset.column_names)
    elif "messages" not in dataset.column_names:
        raise ValueError(
            f"Dataset '{dataset_name}' doesn't have a 'messages' column and no "
            "formatter is registered for it. Add a formatter in data/formatters.py."
        )

    # Step 2: apply the tokenizer's chat template
    dataset = dataset.map(
        lambda ex: apply_chat_template_for_sft(ex, tokenizer),
        remove_columns=["messages"],
    )
    return dataset


# ── DPO / ORPO formatting ─────────────────────────────────────────────────────

def format_ultrafeedback_for_dpo(example: dict[str, Any]) -> dict[str, Any]:
    """Convert an UltraFeedback row into the (prompt, chosen, rejected) format.

    The UltraFeedback dataset already has "prompt", "chosen", "rejected" columns
    but the chosen/rejected values are lists of messages. We format them with
    the chat template format (as plain strings — the trainer handles tokenisation).

    What is DPO?
    ────────────
    DPO teaches the model to prefer "chosen" responses over "rejected" ones.
    The model implicitly learns a preference model without training a separate
    reward model. It's much simpler than PPO-based RLHF.
    """
    # UltraFeedback stores chosen/rejected as [{"role": ..., "content": ...}, ...]
    # We extract just the last assistant turn as the response text
    def extract_response(messages: list[dict[str, str]]) -> str:
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                return msg["content"]
        return ""

    return {
        "prompt": example["prompt"],
        "chosen": extract_response(example["chosen"]),
        "rejected": extract_response(example["rejected"]),
    }


def prepare_dpo_dataset(dataset: Dataset, dataset_name: str = "") -> Dataset:
    """Full pipeline: raw dataset → (prompt, chosen, rejected) for DPO/ORPO."""
    if "ultrafeedback" in dataset_name.lower():
        dataset = dataset.map(
            format_ultrafeedback_for_dpo,
            remove_columns=dataset.column_names,
        )
    elif not all(c in dataset.column_names for c in ["prompt", "chosen", "rejected"]):
        raise ValueError(
            f"Dataset '{dataset_name}' must have 'prompt', 'chosen', 'rejected' columns "
            "for DPO/ORPO training. Add a formatter in data/formatters.py."
        )
    return dataset


# ── GRPO formatting ───────────────────────────────────────────────────────────

def prepare_grpo_dataset(dataset: Dataset) -> Dataset:
    """Ensure a dataset has the 'prompt' column required by GRPOTrainer.

    GRPO (Group Relative Policy Optimization) works differently from DPO.
    Instead of learning from human-labelled preferences, it generates multiple
    responses and scores them using a reward function you define.

    The dataset just needs prompts — the trainer generates responses on-the-fly
    and scores them with your reward function.
    """
    if "prompt" not in dataset.column_names:
        raise ValueError(
            "GRPO requires a 'prompt' column in the dataset. "
            "Add a formatter in data/formatters.py for your dataset."
        )
    return dataset
