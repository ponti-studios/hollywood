"""Task extraction and management commands."""

from datetime import datetime
from typing import Annotated, List

import typer
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel

from nexus.lib.clients.openai import openai_chat
from nexus.lib.prompts import get_prompt

app = typer.Typer(name="tasks", help="Task extraction commands")


class Task(BaseModel):
    """A task with optional due date."""

    task: str
    due_date: str | None = None


class TaskList(BaseModel):
    """List of extracted tasks."""

    tasks: List[Task]


@app.command()
def extract(
    text: Annotated[str, typer.Argument(help="Text containing tasks to extract")],
    json_output: Annotated[bool, typer.Option("--json", "-j")] = False,
) -> None:
    """Extract tasks from natural language text."""
    structured_llm = openai_chat.with_structured_output(TaskList)

    examples = [
        [
            "human",
            "Today's Date: 2025-01-31 \n I have to go to the gym tomorrow, and pick up some groceries today",
        ],
        [
            "assistant",
            str(
                {
                    "tasks": [
                        {"task": "go to the gym", "due_date": "2025-02-01"},
                        {"task": "pick up some groceries", "due_date": "2025-01-31"},
                    ]
                }
            ),
        ],
    ]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", get_prompt("tasks")),
            MessagesPlaceholder("examples", optional=True),
            ("human", "{input}"),
        ]
    )

    chain = {"input": RunnablePassthrough()} | prompt.partial(examples=examples) | structured_llm
    date_str = "Today's Date: " + datetime.now().strftime("%Y-%m-%d")
    response = chain.invoke({"input": f"{date_str}\n{text}"})

    if json_output:
        typer.echo(response.model_dump_json(indent=2))
    else:
        typer.echo("\nExtracted Tasks:")
        for task in response.tasks:
            due = task.due_date or "No due date"
            typer.echo(f"  - {task.task} (due: {due})")


if __name__ == "__main__":
    app()
