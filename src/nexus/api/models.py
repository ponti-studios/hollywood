from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nexus.runs.schema import RunSchema


class ApiHealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ok": True,
                    "service": "nexus",
                    "api": "control-plane",
                    "capabilities": ["text", "audio", "experiments", "runs"],
                }
            ]
        }
    )

    ok: bool = Field(description="Whether the API is healthy.")
    service: str = Field(description="Service name.")
    api: str = Field(description="API role or topology label.")
    capabilities: list[str] = Field(description="Top-level capabilities exposed by the API.")


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "model": "HuggingFaceTB/SmolLM2-135M-Instruct",
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "max_tokens": 32,
                    "temperature": 0.7,
                    "stream": False,
                }
            ]
        }
    )

    model: str = Field(description="Model identifier to use for generation.")
    messages: list[ChatMessage] = Field(description="Conversation messages to continue from.")
    max_tokens: int = Field(
        default=512,
        gt=0,
        description="Maximum number of new tokens to generate.",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for non-deterministic generation.",
    )
    stream: bool = Field(
        default=False, description="Whether to stream tokens as server-sent events."
    )
    stop: list[str] | None = Field(
        default=None,
        description="Optional stop sequences that truncate the returned completion.",
    )


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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"model_id": "HuggingFaceTB/SmolLM2-135M-Instruct", "quantize": "4bit"}]
        }
    )

    model_id: str = Field(description="Registered model identifier to load.")
    quantize: Literal["4bit", "8bit"] | None = Field(
        default=None,
        description="Optional quantization mode for backends that support it.",
    )


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "nexus"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


class ModelOperationResponse(BaseModel):
    status: str = Field(description="Operation status.")
    model_id: str = Field(description="Model identifier affected by the operation.")


class RunResponse(RunSchema):
    """Temporary API alias for the canonical platform run schema.

    Keep this alias while the API models module remains the import home for
    route response models. Over time, routes can import `RunSchema` directly.
    """
