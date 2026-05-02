"""
Shared test fixtures and configuration.

These fixtures are automatically available to all test files in this directory.
pytest loads conftest.py before any tests run.
"""

import pytest


@pytest.fixture
def sample_recipe_dict() -> dict:
    """A minimal valid recipe dictionary for testing config parsing."""
    return {
        "name": "test-recipe",
        "description": "A test recipe",
        "model": {
            "model_id": "google/gemma-4-e2b",
            "dtype": "bfloat16",
            "max_seq_len": 512,
        },
        "data": {
            "dataset_name": "tatsu-lab/alpaca",
            "split": "train",
            "max_samples": 100,
        },
        "training": {
            "method": "sft",
            "learning_rate": 2e-4,
            "num_epochs": 1,
            "batch_size": 2,
        },
        "lora": {
            "r": 8,
            "alpha": 16,
        },
    }
