"""
Tests for the data pipeline.

These tests use a tiny synthetic dataset so they run without downloading
anything from HuggingFace.
"""

import pytest
from datasets import Dataset


class TestAlpacaFormatter:
    def test_basic_instruction(self):
        from nexus.data.formatters import format_alpaca_for_sft

        row = {
            "instruction": "Write a poem about the ocean.",
            "input": "",
            "output": "The ocean is vast and deep…",
        }
        result = format_alpaca_for_sft(row)

        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][1]["role"] == "assistant"
        assert "ocean" in result["messages"][0]["content"]

    def test_instruction_with_input(self):
        from nexus.data.formatters import format_alpaca_for_sft

        row = {
            "instruction": "Translate to French.",
            "input": "Hello, world!",
            "output": "Bonjour, monde!",
        }
        result = format_alpaca_for_sft(row)

        # When input is present, it should be combined with the instruction
        assert "Translate to French" in result["messages"][0]["content"]
        assert "Hello, world!" in result["messages"][0]["content"]


class TestDPOFormatter:
    def test_ultrafeedback_row(self):
        from nexus.data.formatters import format_ultrafeedback_for_dpo

        row = {
            "prompt": "What is 2+2?",
            "chosen": [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
            ],
            "rejected": [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "5"},
            ],
        }
        result = format_ultrafeedback_for_dpo(row)

        assert result["prompt"] == "What is 2+2?"
        assert result["chosen"] == "4"
        assert result["rejected"] == "5"

    def test_ultrafeedback_row_without_explicit_prompt_field(self):
        from nexus.data.formatters import format_ultrafeedback_for_dpo

        row = {
            "chosen": [
                {"role": "user", "content": "Write a snake game."},
                {"role": "assistant", "content": "Use pygame and start with..."},
            ],
            "rejected": [
                {"role": "user", "content": "Write a snake game."},
                {"role": "assistant", "content": "Just use random code."},
            ],
        }
        result = format_ultrafeedback_for_dpo(row)

        assert result["prompt"] == "Write a snake game."
        assert result["chosen"] == "Use pygame and start with..."
        assert result["rejected"] == "Just use random code."

    def test_prepare_dpo_raises_on_missing_columns(self):
        from nexus.data.formatters import prepare_dpo_dataset

        bad_dataset = Dataset.from_list([{"text": "hello"}])
        with pytest.raises(ValueError, match="must have 'prompt', 'chosen', 'rejected'"):
            prepare_dpo_dataset(bad_dataset, dataset_name="unknown-dataset")


class TestGRPOFormatter:
    def test_raises_on_missing_prompt(self):
        from nexus.data.formatters import prepare_grpo_dataset

        bad_dataset = Dataset.from_list([{"question": "What is 2+2?"}])
        with pytest.raises(ValueError, match="'prompt' column"):
            prepare_grpo_dataset(bad_dataset)

    def test_accepts_standard_grpo_prompt_rows(self):
        from nexus.data.formatters import prepare_grpo_dataset

        good_dataset = Dataset.from_list([{"prompt": "What is 2+2?", "answer": "4"}])
        result = prepare_grpo_dataset(good_dataset)
        assert "prompt" in result.column_names
