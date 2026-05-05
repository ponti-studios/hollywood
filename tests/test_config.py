"""
Tests for the config module.

Why test configs?
─────────────────
Config bugs are especially painful in ML because they often fail silently —
the wrong learning rate doesn't crash the program, it just produces a bad model.

Testing that Pydantic models correctly validate and reject configs ensures
you get loud errors at startup rather than silent training failures.
"""

import pytest
from pydantic import ValidationError

from nexus.config import LoraConfig, ModelConfig, Recipe, TrainingConfig


class TestModelConfig:
    def test_valid_config(self):
        cfg = ModelConfig(model_id="google/gemma-4-e2b")
        assert cfg.model_id == "google/gemma-4-e2b"
        assert cfg.dtype == "bfloat16"  # correct default
        assert cfg.max_seq_len == 2048
        assert cfg.attn_implementation == "eager"

    def test_invalid_dtype_rejected(self):
        with pytest.raises(ValidationError):
            ModelConfig(model_id="google/gemma-4-e2b", dtype="float16")

    def test_model_id_required(self):
        with pytest.raises(ValidationError):
            ModelConfig()  # type: ignore


class TestLoraConfig:
    def test_valid_config(self):
        cfg = LoraConfig(r=16, alpha=32)
        assert cfg.rank == 16
        assert cfg.alpha == 32
        assert "q_proj" in cfg.target_modules

    def test_rank_alias(self):
        # rank can be specified as 'r' (the LoRA paper convention)
        cfg = LoraConfig(r=8, alpha=16)
        assert cfg.rank == 8

    def test_zero_rank_rejected(self):
        with pytest.raises(ValidationError):
            LoraConfig(r=0, alpha=0)

    def test_negative_rank_rejected(self):
        with pytest.raises(ValidationError):
            LoraConfig(r=-1, alpha=16)


class TestTrainingConfig:
    def test_valid_sft_config(self):
        cfg = TrainingConfig(method="sft")
        assert cfg.method == "sft"
        assert cfg.learning_rate == 2e-4
        assert cfg.fp16 is False  # MUST be False for Gemma

    def test_fp16_always_false(self):
        # Even if you try to set fp16=True, it should be forced to False
        cfg = TrainingConfig(method="sft", fp16=True)
        assert cfg.fp16 is False  # validator forces this

    def test_all_methods_valid(self):
        for method in ["sft", "dpo", "orpo", "simpo", "grpo"]:
            cfg = TrainingConfig(method=method)
            assert cfg.method == method

    def test_invalid_method_rejected(self):
        with pytest.raises(ValidationError):
            TrainingConfig(method="rlhf")  # not a supported method


class TestRecipe:
    def test_recipe_from_dict(self, sample_recipe_dict):
        recipe = Recipe(**sample_recipe_dict)
        assert recipe.name == "test-recipe"
        assert recipe.model.model_id == "google/gemma-4-e2b"
        assert recipe.lora is not None
        assert recipe.lora.rank == 8

    def test_recipe_without_lora(self, sample_recipe_dict):
        del sample_recipe_dict["lora"]
        recipe = Recipe(**sample_recipe_dict)
        assert recipe.lora is None

    def test_resolve_output_dir(self, sample_recipe_dict):
        recipe = Recipe(**sample_recipe_dict)
        output_dir = recipe.resolve_output_dir()
        assert "test-recipe" in str(output_dir)

    def test_from_yaml(self, tmp_path, sample_recipe_dict):
        import yaml

        yaml_file = tmp_path / "test_recipe.yaml"
        yaml_file.write_text(yaml.dump(sample_recipe_dict))

        recipe = Recipe.from_yaml(yaml_file)
        assert recipe.name == "test-recipe"
