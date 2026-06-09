"""OpenAI-compatible FastAPI gateway."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from api.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ModelCard,
    ModelListResponse,
)
from vllm.client import VLLMClient

load_dotenv()

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("api.access")

app = FastAPI(
    title="model-serving-stack",
    version="0.1.0",
    description="Unified OpenAI-compatible gateway for the NVIDIA model serving stack.",
)
client = VLLMClient()


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log structured request metadata and attach X-Request-ID."""

    _SKIP_PATHS = {"/health", "/metrics"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        access_logger.info(
            "api_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            },
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Backend"] = "vllm"
        return response


app.add_middleware(StructuredLoggingMiddleware)


def _load_model_registry() -> list[ModelCard]:
    config_path = Path("configs/models.yaml")
    if not config_path.exists():
        return [ModelCard(id="meta/llama3-8b-instruct")]
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    models = []
    for entry in data.get("models", []):
        name = entry.get("name") or entry.get("path")
        if name:
            models.append(ModelCard(id=str(name)))
    return models or [ModelCard(id="meta/llama3-8b-instruct")]


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """Return models configured in configs/models.yaml."""
    return ModelListResponse(data=_load_model_registry())


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Proxy chat completions to the configured vLLM backend."""
    try:
        response_text = client.chat(
            messages=[message.model_dump() for message in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as exc:
        logger.exception("Chat completion failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        model=request.model,
        choices=[
            ChatCompletionChoice(
                message=ChatMessage(role="assistant", content=response_text),
            )
        ],
    )


@app.get("/health")
async def health():
    return {"status": "ok", "vllm_ready": client.health_check()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
