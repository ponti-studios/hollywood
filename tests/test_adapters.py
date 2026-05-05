from __future__ import annotations

import pytest

pytest.importorskip("peft")
pytest.importorskip("torch")

import torch

from nexus.models.adapters import _resolve_lora_target_modules


class _ClippableLinear(torch.nn.Module):
    def __init__(self, in_features: int = 4, out_features: int = 4) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(in_features, out_features, bias=False)


class _SelfAttention(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.q_proj = torch.nn.Linear(4, 4, bias=False)
        self.k_proj = torch.nn.Linear(4, 4, bias=False)
        self.v_proj = torch.nn.Linear(4, 4, bias=False)
        self.o_proj = torch.nn.Linear(4, 4, bias=False)


class _TextLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.self_attn = _SelfAttention()


class _TextBackbone(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList([_TextLayer()])


class _VisionLayer(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.self_attn = torch.nn.Module()
        self.self_attn.q_proj = _ClippableLinear()
        self.self_attn.k_proj = _ClippableLinear()
        self.self_attn.v_proj = _ClippableLinear()
        self.self_attn.o_proj = _ClippableLinear()


class _VisionBackbone(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = torch.nn.ModuleList([_VisionLayer()])


class _Gemma4LikeModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.model = torch.nn.Module()
        self.model.language_model = _TextBackbone()
        self.model.vision_tower = _VisionBackbone()


@pytest.mark.parametrize("targets", [["q_proj", "k_proj", "v_proj", "o_proj"]])
def test_resolve_lora_targets_only_picks_text_backbone(targets: list[str]) -> None:
    model = _Gemma4LikeModel()

    resolved = _resolve_lora_target_modules(model, targets)

    assert resolved == [
        "model.language_model.layers.0.self_attn.k_proj",
        "model.language_model.layers.0.self_attn.o_proj",
        "model.language_model.layers.0.self_attn.q_proj",
        "model.language_model.layers.0.self_attn.v_proj",
    ]
    assert all("vision_tower" not in name for name in resolved)


def test_resolve_lora_targets_falls_back_for_plain_text_model() -> None:
    model = _TextBackbone()

    resolved = _resolve_lora_target_modules(model, ["q_proj", "k_proj"])

    assert resolved == [
        "layers.0.self_attn.k_proj",
        "layers.0.self_attn.q_proj",
    ]
