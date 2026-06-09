# Subagent: api-schema-polish

**Invoke:** `/api-schema-polish`
**Repo:** model-serving-stack
**Task Ref:** TASKS.md §2.2
**Estimated Time:** 25 min

---

## Objective

Polish `api/main.py` to be a fully production-grade, OpenAI-compatible serving API: Pydantic v2 models with validators, OpenAPI docstrings on all routes, exact OpenAI `/v1/chat/completions` response schema, and a new `GET /v1/models` endpoint driven by `configs/models.yaml`.

---

## Context

- The API is a FastAPI app in `api/main.py`.
- It currently serves `/v1/chat/completions`, `/health`, and `/metrics`.
- `configs/models.yaml` already exists with model definitions — read it to build the `/v1/models` response.
- This is the NVIDIA SA portfolio repo; the API must match OpenAI wire format exactly so any OpenAI SDK client works without modification.

---

## Step-by-Step Instructions

### Step 1 — Read current api/main.py

```bash
cat api/main.py
cat configs/models.yaml
```

Note: current request/response models, route signatures, existing middleware.

---

### Step 2 — Define Pydantic v2 request/response models

Add or update to `api/models.py` (create if missing):

```python
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
import time
import uuid

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model ID to use for completion")
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)
    stream: bool = Field(default=False)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    n: int = Field(default=1, ge=1, le=8)

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length", "content_filter", "tool_calls"] = "stop"

class UsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:8]}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageStats

class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "nvidia"

class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelCard]
```

---

### Step 3 — Add OpenAPI docstrings to all routes

Update each route in `api/main.py` with a docstring that appears in the OpenAPI spec:

```python
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """
    OpenAI-compatible chat completion endpoint.
    
    Routes to the appropriate backend (vLLM, Triton, Ray Serve) based on the 
    `model` field in the request. Compatible with any OpenAI SDK client.
    """
    ...

@app.get("/health")
async def health_check():
    """
    Liveness and readiness check.
    
    Returns per-backend health status. Returns 200 if any backend is healthy,
    503 if all backends are unavailable.
    """
    ...

@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Exposes `api_requests_total` and `api_request_latency_seconds` histograms.
    Compatible with Prometheus scrape config.
    """
    ...
```

---

### Step 4 — Add GET /v1/models endpoint

```python
import yaml
from pathlib import Path

@app.get("/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """
    List available models.
    
    Returns models defined in configs/models.yaml. Compatible with OpenAI
    /v1/models endpoint. Use the returned model IDs in chat completion requests.
    """
    models_path = Path("configs/models.yaml")
    raw = yaml.safe_load(models_path.read_text())
    models = [
        ModelCard(
            id=m["id"],
            created=m.get("created", 0),
            owned_by=m.get("owned_by", "nvidia"),
        )
        for m in raw.get("models", [])
    ]
    return ModelListResponse(data=models)
```

---

### Step 5 — Verify Swagger UI renders

```bash
uvicorn api.main:app --reload &
curl -s http://localhost:8000/openapi.json | python -m json.tool | head -50
curl http://localhost:8000/v1/models
```

- `GET /docs` must render Swagger UI without 422 errors
- `GET /v1/models` must return a valid `ModelListResponse` JSON
- `GET /openapi.json` must include descriptions for all routes

---

### Step 6 — Type-check

```bash
mypy --strict api/main.py api/models.py
```

Fix any mypy errors before marking done.

---

## Acceptance Criteria

- [ ] `GET /docs` (Swagger UI) renders without errors and shows descriptions for all routes
- [ ] `GET /v1/models` returns models from `configs/models.yaml` in OpenAI format
- [ ] `/v1/chat/completions` response schema matches OpenAI API format exactly (id, object, created, model, choices, usage)
- [ ] All routes have docstrings visible in `GET /openapi.json`
- [ ] `mypy --strict api/main.py` exits 0
- [ ] Existing tests in `tests/` still pass

---

## Do NOT

- Do NOT change the `/health` or `/metrics` paths
- Do NOT add authentication — that is out of scope for this task
- Do NOT break the `StructuredLoggingMiddleware` if it was added by `/add-api-logging`
- Do NOT hardcode model IDs — always read from `configs/models.yaml`
