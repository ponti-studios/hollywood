"""Vision/image processing commands."""

import base64
from pathlib import Path
from typing import Annotated

import typer

from nexus.lib.clients.openai import openai_client

app = typer.Typer(name="vision", help="Image analysis commands")


def get_image_description(image_bytes: bytes) -> str:
    """Get image description using GPT-4 Vision."""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    return completion.choices[0].message.content or ""


@app.command()
def describe(
    image: Annotated[Path, typer.Argument(help="Image file to analyze")],
    prompt: Annotated[str, typer.Option("--prompt", "-p")] = "What's in this image?",
) -> None:
    """Describe the contents of an image using GPT-4 Vision."""
    if not image.exists():
        typer.echo(f"Error: File not found: {image}", err=True)
        raise typer.Exit(1)

    with open(image, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    # Determine media type from extension
    suffix = image.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{base64_image}"},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    content = completion.choices[0].message.content
    if content:
        typer.echo(content)


@app.command()
def embedding(
    image: Annotated[Path, typer.Argument(help="Image file to get embedding for")],
) -> None:
    """Get text embedding from image description."""
    if not image.exists():
        typer.echo(f"Error: File not found: {image}", err=True)
        raise typer.Exit(1)

    # First describe the image
    with open(image, "rb") as f:
        image_bytes = f.read()

    description = get_image_description(image_bytes)

    # Get embedding from description
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002",
        input=description,
    )

    typer.echo(f"Description: {description[:100]}...")
    typer.echo(f"Embedding dimension: {len(response.data[0].embedding)}")


if __name__ == "__main__":
    app()
