from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from nexus.api.models import LoadModelRequest
from nexus.config import ModelConfig
from nexus.experiments.config import ModelSpec
from nexus.models.policy import GEMMA_TEXT_MODEL_ID, write_model_manifest


def test_remote_gemma_model_is_allowed() -> None:
    cfg = ModelConfig(model_id=GEMMA_TEXT_MODEL_ID)
    assert cfg.model_id == GEMMA_TEXT_MODEL_ID


def test_non_default_gemma_family_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelConfig(model_id="google/gemma-4-E4B-it")


def test_local_checkpoint_requires_nexus_manifest(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint"
    write_model_manifest(checkpoint)

    cfg = ModelConfig(model_id=str(checkpoint))
    assert cfg.model_id == str(checkpoint)


def test_adapter_only_checkpoint_is_rejected(tmp_path: Path) -> None:
    checkpoint = tmp_path / "adapter-checkpoint"
    write_model_manifest(checkpoint, checkpoint_kind="adapter")

    with pytest.raises(ValidationError):
        ModelConfig(model_id=str(checkpoint))


def test_experiment_model_spec_uses_same_policy(tmp_path: Path) -> None:
    checkpoint = tmp_path / "spec-checkpoint"
    write_model_manifest(checkpoint)

    spec = ModelSpec(model_id=str(checkpoint), role="large")
    assert spec.model_id == str(checkpoint)


def test_experiment_model_spec_rejects_non_default_remote() -> None:
    with pytest.raises(ValidationError):
        ModelSpec(model_id="google/gemma-4-E4B-it", role="large")


def test_api_load_request_uses_same_policy(tmp_path: Path) -> None:
    checkpoint = tmp_path / "api-checkpoint"
    write_model_manifest(checkpoint)

    request = LoadModelRequest(model_id=str(checkpoint), quantize="4bit")
    assert request.model_id == str(checkpoint)

    with pytest.raises(ValidationError):
        LoadModelRequest(model_id="google/gemma-4-31B-it")
