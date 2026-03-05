"""Utility tools and commands."""

from typing import Annotated

import typer
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel

from nexus.lib.clients.openai import openai_chat
from nexus.lib.prompts import get_prompt

app = typer.Typer(name="tools", help="Utility tools")


class WriterOutput(BaseModel):
    """Output from the writer tool."""

    text: str


@app.command()
def writer(
    text: Annotated[str, typer.Argument(help="Text to process")],
    raw: Annotated[bool, typer.Option("--raw", "-r")] = False,
) -> None:
    """Process text through the AI writer tool."""
    structured_llm = openai_chat.with_structured_output(WriterOutput)

    prompt = PromptTemplate(
        template=get_prompt("writer"),
        input_variables=["user_input"],
    )

    chain = {"user_input": RunnablePassthrough()} | prompt | structured_llm
    response = chain.invoke({"user_input": text})

    typer.echo(response.text)


if __name__ == "__main__":
    app()
