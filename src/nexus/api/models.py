from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int = Field(default=512, gt=0)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage


class LoadModelRequest(BaseModel):
    model_id: str
    quantize: Literal["4bit", "8bit"] | None = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "nexus"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]
