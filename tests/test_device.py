"""
Tests for device detection utilities.
"""

import pytest

torch = pytest.importorskip("torch")

from nexus.device import (
    estimate_model_memory_gb,
    get_device,
    get_dtype,
    get_torch_device,
    is_apple_silicon,
)


def test_get_device_returns_valid_string():
    device = get_device()
    assert device in ("mps", "cpu")


def test_get_torch_device_returns_device():
    device = get_torch_device()
    assert isinstance(device, torch.device)


def test_get_dtype_returns_torch_dtype():
    dtype = get_dtype()
    assert dtype in (torch.bfloat16, torch.float32)


def test_is_apple_silicon_is_bool():
    result = is_apple_silicon()
    assert isinstance(result, bool)


def test_estimate_memory_1b_bfloat16():
    # A small Gemma-class model can have ~1 billion parameters
    # In bfloat16 (2 bytes/param) that's ~2 GB
    gb = estimate_model_memory_gb(1_000_000_000, dtype=torch.bfloat16)
    assert 1.5 < gb < 2.5  # should be close to 2 GB


def test_estimate_memory_4b_bfloat16():
    # A 4B-class model is roughly 8 GB in bfloat16
    gb = estimate_model_memory_gb(4_000_000_000, dtype=torch.bfloat16)
    assert 7.0 < gb < 9.0


def test_estimate_memory_float32_is_double():
    gb_bf16 = estimate_model_memory_gb(1_000_000_000, dtype=torch.bfloat16)
    gb_fp32 = estimate_model_memory_gb(1_000_000_000, dtype=torch.float32)
    assert abs(gb_fp32 / gb_bf16 - 2.0) < 0.01   # float32 uses exactly 2× the memory
