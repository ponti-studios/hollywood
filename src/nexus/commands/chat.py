"""Chat commands using OpenAI."""

from typing import Annotated

import typer

from nexus.lib.clients.openai import openai_client

app = typer.Typer(name="chat", help="AI chat commands")


@app.command()
def message(
    text: Annotated[str, typer.Argument(help="Message to send")],
    model: Annotated[str, typer.Option("--model", "-m")] = "gpt-4o-mini",
) -> None:
    """Send a message to the AI and get a response."""
    response = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    content = response.choices[0].message.content
    if content:
        typer.echo(content)


@app.command()
def stream(
    text: Annotated[str, typer.Argument(help="Message to send")],
    model: Annotated[str, typer.Option("--model", "-m")] = "gpt-4o-mini",
) -> None:
    """Send a message and stream the response."""
    stream_response = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": text}],
        stream=True,
    )

    typer.echo("Streaming response:")
    for chunk in stream_response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            typer.echo(delta.content, nl=False)
    typer.echo()


if __name__ == "__main__":
    app()
