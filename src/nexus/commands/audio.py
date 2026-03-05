"""Audio processing commands."""

from pathlib import Path
from typing import Annotated

import typer

from nexus.lib.clients.openai import openai_client

app = typer.Typer(name="audio", help="Audio processing commands")


@app.command()
def transcribe(
    file: Annotated[Path, typer.Argument(help="Audio file to transcribe")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Transcribe an audio file using Whisper."""
    if not file.exists():
        typer.echo(f"Error: File not found: {file}", err=True)
        raise typer.Exit(1)

    with open(file, "rb") as audio_file:
        transcription = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    if output:
        output.write_text(transcription.text)
        typer.echo(f"Transcription saved to: {output}")
    else:
        typer.echo(transcription.text)


if __name__ == "__main__":
    app()
