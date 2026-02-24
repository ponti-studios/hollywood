from typing import Annotated
from fastapi import APIRouter, Form
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel

from snakesss.lib.clients.openai import openai_chat
from snakesss.lib.file_service import FileRepository

router = APIRouter(prefix="/tools")


class WriterOutput(BaseModel):
    text: str


@router.post("/writer")
def writer_tool(input: Annotated[str, Form(...)]):
    structured_llm = openai_chat.with_structured_output(WriterOutput)

    prompt = PromptTemplate(
        template=FileRepository.get_file_contents("prompts/writer.md"),
        partial_variables={"user_input": WriterOutput.model_json_schema()},
        input_variables=["user_input"],
    )

    chain = {"user_input": RunnablePassthrough()} | prompt | structured_llm

    response = chain.invoke({"user_input": input})

    return {"content": response}
