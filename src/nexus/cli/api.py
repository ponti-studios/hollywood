from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

api_app = typer.Typer(no_args_is_help=True)
console = Console()


@api_app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address."),
    port: int = typer.Option(8787, "--port", "-p", help="Port to listen on."),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload (dev only)."),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes."),
) -> None:
    """Start the Nexus control-plane API.

    Provides multimodal platform endpoints for text, audio,
    experiments, and run history.
    The compose stack starts the text and audio backends automatically.
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn is required. Install with: pip install 'nexus[api]'[/red]")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"Host:    {host}\n"
            f"Port:    {port}\n"
            f"URL:     http://{host}:{port}\n"
            f"Docs:    http://{host}:{port}/docs\n"
            f"Health:  http://{host}:{port}/health",
            title="Nexus Control Plane",
            border_style="green",
        )
    )

    uvicorn.run(
        "nexus.api.app:app",
        host=host,
        port=port,
        reload=reload,
        workers=1 if reload else workers,
    )
