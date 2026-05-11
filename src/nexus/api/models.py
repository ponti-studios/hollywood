from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiHealthResponse(BaseModel):
    ok: bool
    service: str = "nexus"
    api: str = "openai-first"
    capabilities: list[str]
    providers: dict[str, bool]
    models: dict[str, str]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class Usage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class TextReplyRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": "What is 2+2?",
                    "max_tokens": 32,
                    "temperature": 0.7,
                }
            ]
        }
    )

    prompt: str = Field(min_length=1)
    model: str | None = None
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stop: list[str] | None = None


class TextReplyResponse(BaseModel):
    text: str
    model: str
    provider: str = "openai"
    usage: Usage = Field(default_factory=Usage)


class TextChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "messages": [{"role": "user", "content": "Explain gravity"}],
                    "max_tokens": 64,
                    "temperature": 0.7,
                }
            ]
        }
    )

    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stop: list[str] | None = None


class TextChatResponse(BaseModel):
    message: ChatMessage
    model: str
    provider: str = "openai"
    usage: Usage = Field(default_factory=Usage)


TextInput = Annotated[str, Field(min_length=1)]


class ImageAnalyzeResponse(BaseModel):
    text: str
    model: str
    provider: str = "openai"
    usage: Usage = Field(default_factory=Usage)


class TextAnalyzeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "texts": ["Lunch with Alex", "Project sync with Taylor"],
                }
            ]
        }
    )

    texts: list[TextInput] = Field(min_length=1)
    model: str | None = None


class TextAnalyzeItem(BaseModel):
    input: str
    cleaned_text: str
    people: list[str] = Field(default_factory=list)


class TextAnalyzeResponse(BaseModel):
    results: list[TextAnalyzeItem]
    model: str
    provider: str = "openai"
    usage: Usage = Field(default_factory=Usage)
