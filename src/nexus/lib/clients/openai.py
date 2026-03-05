from typing import Annotated, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import AsyncOpenAI, OpenAI
from pydantic import SecretStr, StringConstraints
from nexus.config import settings

OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY

USE_OPENROUTER = bool(OPENROUTER_API_KEY)

if USE_OPENROUTER:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set")
    base_url = "https://openrouter.ai/api/v1"
    extra_headers = {"HTTP-Referer": "https://github.com/charlesponti/nexus"}
    api_key = OPENROUTER_API_KEY
    default_model = "openai/gpt-4o-mini"
else:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    base_url = None
    extra_headers = None
    api_key = OPENAI_API_KEY
    default_model = "gpt-4o-mini"

openai_client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    default_headers=extra_headers,
)

openai_async_client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url,
    default_headers=extra_headers,
)

openai_chat = ChatOpenAI(
    model=default_model,
    api_key=SecretStr(api_key),
    base_url=base_url,
    default_headers=extra_headers,
)

openai_embeddings = OpenAIEmbeddings(
    api_key=SecretStr(api_key),
    base_url=base_url,
)


def get_openai_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    embeddings = response.data[0].embedding

    return embeddings


async def get_openai_chat_completion(
    system_message,
    user_message,
    model: Annotated[Optional[str], StringConstraints(pattern=r"^gpt-*$")] = None,
):
    response = openai_client.chat.completions.create(
        model=model or default_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content
