from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel

from nexus.lib.clients.openai import openai_chat


class JobPost(BaseModel):
    benefits: Optional[List[str]] = None
    companyDescription: Optional[str] = None
    companyName: str
    companyWebsite: Optional[str] = None
    compensationRangeEnd: Optional[float] = None
    compensationRangeStart: Optional[float] = None
    employmentType: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    requiredSkills: Optional[List[str]] = None
    jobTitle: str
    roleDescription: Optional[str] = None
    roleIdealCandidate: Optional[str] = None
    roleResponsibilities: Optional[str] = None
    url: Optional[str] = None


def convert_text_to_job_post(text: str) -> JobPost:
    template = """
    You are an expert html and text parser. The user will provide the text from the website of a job posting.
    Extract the following information from the job posting and format as JSON:

    - benefits: An array of benefits offered (null if not found)
    - companyDescription: A description of the company (null if not found)
    - companyName: The name of the company
    - companyWebsite: The company's website URL (null if not found)
    - compensationRangeStart: The lower bound of the salary range as a number (null if not found)
    - compensationRangeEnd: The upper bound of the salary range as a number (null if not found)
    - employmentType: Type of employment like "Full-time", "Part-time", "Contract", etc. (null if not found)
    - industry: The industry the role is in (null if not found)
    - location: Where the job is located (null if not found)
    - requiredSkills: An array of required skills (null if not found)
    - jobTitle: The title of the job
    - roleDescription: Description of the role (null if not found)
    - roleIdealCandidate: Description of the ideal candidate (null if not found)
    - roleResponsibilities: Job responsibilities (null if not found)
    """

    prompt = ChatPromptTemplate.from_messages([("system", template), ("human", "{result}")])
    llm = openai_chat.with_structured_output(JobPost)

    chain = {"result": RunnablePassthrough()} | prompt | llm

    chain_response = chain.invoke({"question": text})
    response = JobPost.model_validate(chain_response)
    return response
