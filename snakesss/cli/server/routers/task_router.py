from datetime import datetime
from fastapi import APIRouter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel
from typing import List

from snakesss.lib.file_service import FileRepository
from snakesss.lib.clients.openai import openai_chat, openai_client

router = APIRouter()


class TaskToolInput(BaseModel):
    input: str


class Tasks(BaseModel):
    task: str
    due_date: str | None


class TaskToolOutput(BaseModel):
    tasks: List[Tasks]


@router.post("/tasks/langchain")
def task_langchain(input: TaskToolInput):
    structured_llm = openai_chat.with_structured_output(TaskToolOutput)
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
                        {"task": "go to the gym", "date": "2025-02-01"},
                        {"task": "pick up some groceries", "date": "2025-01-31"},
                    ]
                }
            ),
        ],
    ]
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", FileRepository.get_file_contents("prompts/tasks.md")),
            MessagesPlaceholder("examples", optional=True),
            ("human", "{input}"),
        ]
    )

    chain = {"input": RunnablePassthrough()} | prompt.partial(examples=examples) | structured_llm
    date_str = "Today's Date:" + datetime.now().strftime("%Y-%m-%d")
    response = chain.invoke({"input": date_str + "\n" + input.input})

    return response


@router.post("/tasks/openai")
def task_tool_calls(input: TaskToolInput):
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [{"text": "what do i need to do next week", "type": "text"}]},
        ],
        response_format={"type": "text"},
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "required": ["task_name", "due_date", "categories"],
                        "properties": {
                            "due_date": {
                                "type": "string",
                                "description": "The due date and time for the task in ISO 8601 format",
                            },
                            "task_name": {"type": "string", "description": "The name of the task"},
                            "categories": {
                                "type": "array",
                                "items": {"type": "string", "description": "A category for the task"},
                                "description": "Categories to which the task belongs",
                            },
                        },
                        "additionalProperties": False,
                    },
                    "description": "Creates tasks with due date and categories",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "find_tasks",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "required": ["category", "date", "dates_between", "query"],
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "The date to filter tasks by, in YYYY-MM-DD format",
                            },
                            "query": {
                                "type": "string",
                                "description": "The text query to match tasks against",
                            },
                            "category": {"type": "string", "description": "The category to filter tasks by"},
                            "dates_between": {
                                "type": "object",
                                "strict": True,
                                "required": ["date_start", "date_end"],
                                "properties": {
                                    "date_end": {
                                        "type": "string",
                                        "description": "The date to stop finding tasks, in YYYY-MM-DD",
                                    },
                                    "date_start": {
                                        "type": "string",
                                        "description": "The date to start finding tasks, in YYYY-MM-DD",
                                    },
                                },
                                "description": "The date to filter tasks between. To be used when user wants to find tasks in a particular time period such as next week, next month, last year, etc.",
                                "additionalProperties": False,
                            },
                        },
                        "additionalProperties": False,
                    },
                    "description": "Find tasks that match user query based on text or date or category",
                },
            },
        ],
        tool_choice="required",
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    return response.choices[0].message.content
