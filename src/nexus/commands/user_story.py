import csv
import os
import uuid
from datetime import datetime
from typing import List

import typer
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableSerializable
from tqdm import tqdm

from nexus.commands.user_story_basic import UserStory, UserStoryExample, get_user_story_examples
from nexus.lib.clients.openai import openai_chat
from nexus.lib.file_service import FileRepository

system_prompt = FileRepository.get_file_contents("src/nexus/commands/user_story_prompt.md")

user_story_app = typer.Typer(name="user_story")


def create_user_story_generator() -> RunnableSerializable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("examples", optional=True),
            ("human", "{idea}"),
        ]
    )

    structured_llm = openai_chat.with_structured_output(UserStory)
    examples = [msg for example in get_user_story_examples() for msg in tool_example_to_messages(example)]

    chain = {"idea": RunnablePassthrough()} | prompt.partial(examples=examples) | structured_llm

    return chain


def tool_example_to_messages(example: UserStoryExample) -> List[BaseMessage]:
    messages: List[BaseMessage] = [HumanMessage(content=example.input)]
    openai_tool_calls = [
        {
            "id": str(uuid.uuid4()),
            "type": "function",
            "function": {"name": tool_call.__class__.__name__, "arguments": tool_call.model_dump_json()},
        }
        for tool_call in example.tool_calls
    ]

    messages.append(AIMessage(content="", additional_kwargs={"tool_calls": openai_tool_calls}))

    tool_outputs = example.tool_outputs or ["Tool called."] * len(openai_tool_calls)
    messages.extend(
        [
            ToolMessage(content=output, tool_call_id=tool_call["id"])
            for output, tool_call in zip(tool_outputs, openai_tool_calls)
        ]
    )

    return messages


@user_story_app.command(name="generate")
def run(idea: str = typer.Argument(..., help="The idea for the user story")):
    query_analyzer = create_user_story_generator()
    result = query_analyzer.invoke(idea)

    if isinstance(result, UserStory):
        print(result.model_dump_json(indent=2))
    else:
        print("No user story generated", result)


@user_story_app.command(name="generate-from-file")
def run_from_file(
    file_path: str = typer.Argument(..., help="The file path to the idea"),
    end_line: int = typer.Option(None, help="The line number to end at"),
):
    typer.echo(f"Generating user stories from file: {file_path}", color=True)
    query_analyzer = create_user_story_generator()
    lines, _ = FileRepository.get_file_line_items(file_path=file_path)
    lines = lines[:end_line]

    stories = []
    start_time = datetime.now()

    current_line_number = 0
    try:
        for line in tqdm(lines):
            result = query_analyzer.invoke(line)
            if isinstance(result, UserStory):
                stories.append(result)
                current_line_number += 1
    except Exception:
        with open(file_path, "w") as f:
            f.write("\n".join(lines[current_line_number:]))

    process_time = (datetime.now() - start_time).total_seconds()
    print(f"\nTime taken to process file: {process_time:.2f} seconds")
    print(f"Number of user stories generated: {len(stories)}")

    write_start_time = datetime.now()
    write_stories_to_csv(stories)
    write_time = (datetime.now() - write_start_time).total_seconds()

    print(f"\nTime taken to write user stories: {write_time:.2f} seconds")
    print("User stories written to user_stories.csv")


def write_stories_to_csv(stories: List[UserStory]):
    file_exists = os.path.isfile("user_stories.csv")
    with open("user_stories.csv", "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=UserStory.__fields__.keys())
        if not file_exists:
            writer.writeheader()
        for story in stories:
            writer.writerow(story.dict())


if __name__ == "__main__":
    user_story_app()
