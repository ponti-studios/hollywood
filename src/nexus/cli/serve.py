"""
serve.py — Serve a Gemma 4 model locally via MLX-VLM for interactive chat.

Usage:
  nexus serve run --model mlx-community/gemma-4-e2b-bf16
  nexus serve chat --model mlx-community/gemma-4-e2b-bf16
  nexus serve chat --model .data/checkpoints/my-sft-run

Why MLX for serving?
────────────────────
MLX is Apple's native ML framework for M-series chips. For inference,
it's significantly faster than PyTorch MPS because it uses the full
Metal GPU pipeline and unified memory more efficiently.

Gemma 4 for serving
───────────────────
Gemma 4 E2B currently runs through mlx-vlm's MLX conversion:
  mlx-community/gemma-4-e2b-bf16

Install the MLX stack with `make setup-mlx` or `uv pip install -e ".[mlx]"`.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from nexus.runtime import ensure_mlx_runtime

serve_app = typer.Typer(no_args_is_help=True)
console = Console()


@serve_app.command("run")
def run_server(
    model: str = typer.Option(
        "mlx-community/gemma-4-e2b-bf16",
        "--model", "-m",
        help="Model ID (HuggingFace or local path).",
    ),
    quantize: str | None = typer.Option(
        None,
        "--quantize", "-q",
        help="Reserved for older mlx-lm models; Gemma 4 E2B uses the BF16 mlx-vlm build.",
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
        from mlx_vlm import server
    except ImportError:
        console.print("[red]mlx-vlm is required. Install with: pip install mlx-vlm[/red]")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"Model: [cyan]{model}[/cyan]\n"
        f"Port:  {port}\n"
        f"API:   http://localhost:{port}/v1/chat/completions",
        title="MLX Server",
        border_style="green",
    ))

    # Build the mlx-vlm server argument list.
    args = ["--model", model, "--port", str(port)]
    if quantize:
        console.print("[yellow]Ignoring --quantize; Gemma 4 E2B uses the BF16 mlx-vlm build.[/yellow]")

    # mlx-vlm server is a standalone script — invoke it programmatically.
    server.main(args)


@serve_app.command("chat")
def chat(
    model: str = typer.Option(
        "mlx-community/gemma-4-e2b-bf16",
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
    """Start an interactive chat session with a Gemma 4 model in your terminal.

    This is the fastest way to test your fine-tuned models.
    Type 'quit' or press Ctrl+C to exit.

    Tip: point --model at a local checkpoint (e.g. .data/checkpoints/my-sft-run)
    to interactively test your trained model.
    """
    ensure_mlx_runtime(console)

    try:
        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template
    except ImportError:
        console.print("[red]mlx-vlm is required. Install with: pip install mlx-vlm[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Loading:[/bold] {model} …")
    lm, processor = load(model)

    console.print(Panel(
        f"[dim]Model:[/dim] {model}\n"
        f"[dim]System:[/dim] {system}\n\n"
        "Type your message and press Enter. Type [bold]quit[/bold] to exit.",
        title="Gemma 4 Chat",
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

        conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
        prompt = apply_chat_template(processor, lm.config, conversation)

        console.print("\n[bold green]Gemma:[/bold green]", end=" ")

        response = generate(
            model=lm,
            processor=processor,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            verbose=True,
        )
        response_text = response.text if hasattr(response, "text") else str(response)

        history.append({"role": "assistant", "content": response_text})
