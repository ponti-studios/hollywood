"""
device.py — Apple Silicon (MPS) detection and memory utilities.

Why this module?
────────────────
PyTorch can run on multiple "devices":
  - "cpu"   — your main processor, always available but slowest for ML
  - "mps"   — Apple's Metal Performance Shaders, the GPU on M-series chips
  - "cuda"  — NVIDIA GPU (not available on Macs)

This module centralises device detection so the rest of the code never has
to worry about which hardware it's running on.

MPS limitations (as of PyTorch 2.4):
  - No bitsandbytes (QLoRA) — use standard PyTorch tooling for quantised inference
  - No flash attention 2 — use "eager" attention
  - Some operations fall back to CPU automatically (PyTorch handles this)
"""

import platform
from typing import Literal

import torch
from rich.console import Console

console = Console()

DeviceType = Literal["mps", "cpu"]


def get_device() -> DeviceType:
    """Return the best available device for this machine.

    Returns "mps" if running on Apple Silicon with MPS available,
    otherwise falls back to "cpu".
    """
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_torch_device() -> torch.device:
    """Return a torch.device object for the best available device."""
    return torch.device(get_device())


def is_apple_silicon() -> bool:
    """True if running on an Apple M-series chip."""
    return platform.system() == "Darwin" and platform.processor() == "arm"


def get_dtype() -> torch.dtype:
    """Return the recommended floating-point dtype for this device.

    Why bfloat16?
    ─────────────
    bfloat16 (Brain Float 16) uses 16 bits per number (vs. 32 for float32).
    This halves memory usage, allowing larger models to fit on a Mac.

    Gemma was trained in bfloat16 — using float16 can produce NaN values
    because float16 has a smaller range than bfloat16.

    MPS supports bfloat16 on M1 Pro/Max/Ultra and M2+ chips.
    Falls back to float32 if bfloat16 is somehow unavailable.
    """
    if torch.backends.mps.is_available():
        # bfloat16 is supported on MPS (M1 Pro/Max and newer)
        return torch.bfloat16
    return torch.float32


def print_device_info() -> None:
    """Print a summary of the compute environment to the terminal."""
    device = get_device()
    dtype = get_dtype()
    apple = is_apple_silicon()

    console.print("\n[bold]Compute environment[/bold]")
    console.print(f"  Platform    : {platform.platform()}")
    console.print(f"  Device      : [green]{device}[/green]")
    console.print(f"  dtype       : {dtype}")
    console.print(f"  Apple Silicon: {'✓' if apple else '✗'}")
    console.print(f"  MPS available: {'✓' if torch.backends.mps.is_available() else '✗'}")

    if device == "mps":
        # PyTorch does not expose MPS memory stats the same way CUDA does,
        # but we can show allocated memory on newer PyTorch versions.
        try:
            allocated = torch.mps.current_allocated_memory() / 1e9
            console.print(f"  MPS memory allocated: {allocated:.2f} GB")
        except AttributeError:
            pass
    console.print()


def estimate_model_memory_gb(num_params: int, dtype: torch.dtype = torch.bfloat16) -> float:
    """Estimate how much RAM a model will need.

    Rule of thumb: each parameter takes dtype_bytes bytes.
    bfloat16 = 2 bytes/param, float32 = 4 bytes/param.

    This is a lower bound — the actual requirement is higher once you
    account for gradients (~same size as params) and optimiser state
    (Adam keeps 2 extra values per param, so 4× total for full fine-tuning).
    LoRA dramatically reduces this because only adapters are trained.

    Example:
        Gemma models in bfloat16 require roughly 2 bytes per parameter just for weights.
        With LoRA (only adapters trained): adds ~50 MB.
    """
    bytes_per_param = {
        torch.float32: 4,
        torch.bfloat16: 2,
        torch.float16: 2,
    }.get(dtype, 4)
    return (num_params * bytes_per_param) / 1e9
