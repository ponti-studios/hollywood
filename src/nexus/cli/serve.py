"""
serve.py — Serve a Gemma 3 model locally via MLX for interactive chat.

Usage:
  nexus serve run --model google/gemma-3-1b-it
  nexus serve run --model google/gemma-3-4b-it --quantize 4bit
  nexus serve chat --model experiments/my-sft-run

Why MLX for serving?
────────────────────
MLX is Apple's native ML framework for M-series chips. For inference,
it's significantly faster than PyTorch MPS because it uses the full
Metal GPU pipeline and unified memory more efficiently.

Quantisation for serving
────────────────────────
Quantisation reduces model size by representing weights with fewer bits:
  4-bit quantisation: weights stored as 4-bit integers instead of 16-bit
  This cuts memory usage by ~4x at a small quality cost.

  Gemma 3 1B in bfloat16: ~2 GB RAM
  Gemma 3 1B quantised 4-bit: ~0.5 GB RAM

This lets you run both the model AND the judge simultaneously, or fit
the 4B model on a Mac with 8 GB RAM.

MLX community quantised models live at huggingface.co/mlx-community.
They follow the naming pattern: mlx-community/gemma-3-1b-it-4bit
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from nexus.runtime import ensure_mlx_runtime

serve_app = typer.Typer(no_args_is_help=True)
console = Console()


@serve_app.command("run")
def run_server(
    model: str = typer.Option(
        "mlx-community/gemma-3-1b-it-4bit",
        "--model", "-m",
        help="Model ID (HuggingFace or local path). Use mlx-community/ for pre-quantised models.",
    ),
    quantize: Optional[str] = typer.Option(
        None,
        "--quantize", "-q",
        help="Quantise the model on load: '4bit' or '8bit'. Skip if using an mlx-community model.",
    ),
    port: int = typer.Option(8080, "--port", "-p", help="Port for the local HTTP server."),
) -> None:
    """Start a local MLX inference server (OpenAI-compatible API).

    Once running, you can query it with any OpenAI-compatible client:
      curl http://localhost:8080/v1/chat/completions ...

    Or just use `nexus serve chat` for an interactive terminal session.
    """
    ensure_mlx_runtime(console)

    try:
        from mlx_lm import server
    except ImportError:
        console.print("[red]mlx-lm is required. Install with: pip install mlx-lm[/red]")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"Model: [cyan]{model}[/cyan]\n"
        f"Port:  {port}\n"
        f"API:   http://localhost:{port}/v1/chat/completions",
        title="MLX Server",
        border_style="green",
    ))

    # Build the mlx_lm.server argument list
    import sys
    args = ["--model", model, "--port", str(port)]
    if quantize:
        args += ["--quantize"]  # mlx_lm handles 4-bit by default

    # mlx_lm.server is a standalone script — invoke it programmatically
    server.main(args)


@serve_app.command("chat")
def chat(
    model: str = typer.Option(
        "mlx-community/gemma-3-1b-it-4bit",
        "--model", "-m",
        help="Model to chat with (HuggingFace ID or local checkpoint path).",
    ),
    max_tokens: int = typer.Option(512, "--max-tokens", help="Max tokens to generate."),
    temperature: float = typer.Option(0.7, "--temp", help="Sampling temperature."),
    system: str = typer.Option(
        "You are a helpful assistant.",
        "--system",
        help="System prompt to set the model's persona.",
    ),
) -> None:
    """Start an interactive chat session with a Gemma 3 model in your terminal.

    This is the fastest way to test your fine-tuned models.
    Type 'quit' or press Ctrl+C to exit.

    Tip: point --model at a local checkpoint (e.g. experiments/my-sft-run)
    to interactively test your trained model.
    """
    ensure_mlx_runtime(console)

    try:
        from mlx_lm import generate, load
    except ImportError:
        console.print("[red]mlx-lm is required. Install with: pip install mlx-lm[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Loading:[/bold] {model} …")
    lm, tokenizer = load(model)

    console.print(Panel(
        f"[dim]Model:[/dim] {model}\n"
        f"[dim]System:[/dim] {system}\n\n"
        "Type your message and press Enter. Type [bold]quit[/bold] to exit.",
        title="Gemma 3 Chat",
        border_style="cyan",
    ))

    # Maintain conversation history for multi-turn chat
    history: list[dict[str, str]] = [{"role": "system", "content": system}]

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        # Apply chat template to the full conversation history
        prompt = tokenizer.apply_chat_template(
            history,
            tokenize=False,
            add_generation_prompt=True,
        )

        console.print("\n[bold green]Gemma:[/bold green]", end=" ")

        response = generate(
            lm,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            temp=temperature,
            verbose=True,   # streams the response token by token
        )

        history.append({"role": "assistant", "content": response})
