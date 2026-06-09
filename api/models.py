"""OpenAI-compatible API request and response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = Field(default="meta/llama3-8b-instruct", description="Model name from registry")
    messages: list[ChatMessage]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class ChatCompletionChoice(BaseModel):
    """Single completion choice."""

    index: int = 0
    message: ChatMessage
    finish_reason: Literal["stop", "length"] = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    model: str
    choices: list[ChatCompletionChoice]


class ModelCard(BaseModel):
    """Model metadata entry."""

    id: str
    object: Literal["model"] = "model"
    owned_by: str = "local"


class ModelListResponse(BaseModel):
    """OpenAI-compatible model list response."""

    object: Literal["list"] = "list"
    data: list[ModelCard]
