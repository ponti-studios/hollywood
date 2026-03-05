"""Nexus CLI - Main entry point."""

import dotenv  # noqa: E402
import typer  # noqa: E402

dotenv.load_dotenv()

from nexus import __version__  # noqa: E402
from nexus.commands import (  # noqa: E402
    audio,
    chat,
    crawler,
    tasks,
    tools,
    vision,
)
from nexus.commands.user_story import user_story_app  # noqa: E402

app = typer.Typer(
    name="nexus",
    help="Your terminal AI workbench",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
    ctx: typer.Context = typer.Argument(None),
) -> None:
    """Nexus CLI - Your terminal AI workbench."""
    if version:
        typer.echo(f"Nexus v{__version__}")
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(f"Welcome to Nexus v{__version__}!")
        typer.echo("\nRun 'nexus --help' for available commands.")


# Add command groups
app.add_typer(chat.app, name="chat", help="AI chat commands")
app.add_typer(audio.app, name="audio", help="Audio processing commands")
app.add_typer(vision.app, name="vision", help="Image analysis commands")
app.add_typer(tasks.app, name="tasks", help="Task extraction commands")
app.add_typer(tools.app, name="tools", help="Utility tools")
app.add_typer(crawler.app, name="crawler", help="Web scraping commands")
app.add_typer(user_story_app, name="user-story", help="User story generation")


if __name__ == "__main__":
    app()
