from __future__ import annotations

import importlib

import pytest


def test_trainers_package_import_is_lazy() -> None:
    module = importlib.import_module("nexus.trainers")

    assert module.__doc__ is not None
    assert not hasattr(module, "run_dpo")
    assert not hasattr(module, "run_orpo")
    assert not hasattr(module, "run_grpo")
    assert not hasattr(module, "run_sft")


def test_trainer_modules_import_when_trl_is_available() -> None:
    pytest.importorskip("trl")

    for module_name in [
        "nexus.trainers.sft",
        "nexus.trainers.dpo",
        "nexus.trainers.orpo",
        "nexus.trainers.grpo",
    ]:
        module = importlib.import_module(module_name)
        assert module is not None
