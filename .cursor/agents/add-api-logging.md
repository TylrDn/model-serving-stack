---
name: add-api-logging
description: Invoke when adding or modifying the structured request/response logging middleware in the API gateway. Use when the user asks to add logging middleware, implement request tracing, add X-Request-ID headers, log latency metrics, or improve API observability.
model: inherit
readonly: false
is_background: false
---

# Add Structured Request/Response Logging Middleware

## Objective

Update `api/main.py` to add a production-quality `StructuredLoggingMiddleware` that logs every API request and response with structured fields (request_id, method, path, status_code, latency_ms, model). Also add a `X-Request-ID` response header and integrate with the existing Prometheus metrics.

---

## Files to Create / Modify

### Modify: `api/main.py`

Full replacement if the current file lacks middleware. Key additions:

**1. Add structured logging middleware class:**

```python
from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.access")
error_logger = logging.getLogger("api.error")

# ── Prometheus metrics ─────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests",
    labelnames=["method", "path", "status_code", "backend"],
)
REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "API request latency",
    labelnames=["method", "path", "backend"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)
TOKENS_GENERATED = Counter(
    "api_tokens_generated_total",
    "Total tokens generated",
    labelnames=["model", "backend"],
)
```

**2. `StructuredLoggingMiddleware` class (full implementation):**

```python
class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Structured JSON logging for all API requests and responses.
    
    Logs per-request: request_id, method, path, query_string, status_code,
    latency_ms, client_ip, user_agent, content_length_bytes.
    
    Adds X-Request-ID header to every response for distributed tracing.
    Updates Prometheus request_count and latency metrics.
    """
    
    # Paths to skip logging (health checks, metrics)
    _SKIP_PATHS: frozenset[str] = frozenset({"/health", "/metrics", "/favicon.ico"})
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip health/metrics paths to avoid log spam
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)
        
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()
        
        # Try to extract model from request body (non-destructive read)
        model_name = await self._extract_model_name(request)
        
        # Process request
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            error_logger.exception(
                "Unhandled exception",
                extra={"request_id": request_id, "path": request.url.path},
            )
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(
                "api_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.url.query),
                    "status_code": status_code,
                    "latency_ms": round(latency_ms, 2),
                    "client_ip": (request.client.host if request.client else "unknown"),
                    "user_agent": request.headers.get("user-agent", "")[:200],
                    "content_length": request.headers.get("content-length", "0"),
                    "model": model_name or "unknown",
                },
            )
            
            # Determine backend from path prefix
            backend = self._get_backend_from_path(request.url.path)
            
            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status_code=str(status_code),
                backend=backend,
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                path=request.url.path,
                backend=backend,
            ).observe(latency_ms / 1000)
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Backend"] = backend
        return response
    
    async def _extract_model_name(self, request: Request) -> str | None:
        """Non-destructively extract model name from request body if present."""
        if request.method not in ("POST", "PUT"):
            return None
        try:
            body_bytes = await request.body()
            if body_bytes:
                body = json.loads(body_bytes)
                return body.get("model") or body.get("model_name")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None
    
    def _get_backend_from_path(self, path: str) -> str:
        """Infer backend from URL path prefix."""
        if "/vllm" in path:
            return "vllm"
        if "/triton" in path:
            return "triton"
        if "/ray" in path:
            return "ray_serve"
        if "/bento" in path:
            return "bentoml"
        return "gateway"
```

**3. JSON log formatter (configure in lifespan):**

```python
class JSONLogFormatter(logging.Formatter):
    """Format log records as JSON for structured log aggregation (Loki, CloudWatch, etc.)."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge extra fields from logger.info("...", extra={...})
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                log_obj[key] = value
        return json.dumps(log_obj, default=str)
```

**4. Lifespan context manager:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown.
    
    Startup: configure JSON logging, initialize backend connections.
    Shutdown: graceful backend teardown.
    """
    # Configure structured JSON logging
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
    
    logger.info("Model serving stack API starting up", extra={"version": "1.0.0"})
    
    yield  # Application runs here
    
    logger.info("Model serving stack API shutting down")
```

**5. App instantiation and middleware registration:**

```python
app = FastAPI(
    title="Model Serving Stack API",
    description="NVIDIA multi-backend LLM serving gateway (vLLM, Triton, Ray Serve, BentoML)",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost = first to execute)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

**6. Request/Response Pydantic schemas:**

```python
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False
    backend: str = Field(default="vllm", pattern="^(vllm|triton|ray|bento)$")

class ChatResponse(BaseModel):
    id: str
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int]
    backend: str
    latency_ms: float
```

**7. Core route handlers:**

```python
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint. Returns 200 OK when API is ready."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/models")
async def list_models() -> dict[str, Any]:
    """List available models from configs/models.yaml."""
    ...

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, http_request: Request) -> ChatResponse:
    """OpenAI-compatible chat completions endpoint.
    
    Routes to the appropriate backend (vllm, triton, ray, bento) based on request.backend.
    Supports streaming via request.stream=True.
    """
    ...

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
        headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
    )
```

---

### Create: `tests/test_api_middleware.py`

Full test suite for the middleware:

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check_returns_200(client): ...
def test_x_request_id_header_present(client): ...
def test_x_request_id_is_valid_uuid(client): ...
def test_logging_middleware_skips_health_path(client, caplog): ...
def test_logging_middleware_logs_request_fields(client, caplog): ...
def test_logging_middleware_logs_latency_ms(client, caplog): ...
def test_prometheus_metrics_endpoint(client): ...
def test_request_count_incremented_on_post(client): ...

@pytest.mark.parametrize("path,expected_backend", [
    ("/v1/vllm/generate", "vllm"),
    ("/v1/triton/infer", "triton"),
    ("/v1/ray/serve", "ray_serve"),
    ("/v1/chat/completions", "gateway"),
])
def test_backend_detection_from_path(path, expected_backend, client): ...

async def test_async_client_chat_completions(mock_vllm_backend): ...
```

---

## Acceptance Criteria

- [ ] Every non-health API response includes `X-Request-ID` header (valid UUID v4)
- [ ] Every request logs structured JSON: `request_id`, `method`, `path`, `status_code`, `latency_ms`, `client_ip`, `model`
- [ ] `/health` and `/metrics` paths are NOT logged (to avoid noise)
- [ ] Prometheus `/metrics` endpoint returns valid Prometheus text format
- [ ] `api_requests_total` counter increments on each non-health request
- [ ] `api_request_latency_seconds` histogram is updated with correct latency buckets
- [ ] `pytest tests/test_api_middleware.py` passes
- [ ] `mypy --strict api/main.py` exits 0
- [ ] `ruff check api/main.py` exits 0
- [ ] Logging is JSON-formatted (not plain text) when running in production mode
- [ ] `StructuredLoggingMiddleware` handles exceptions without swallowing them
- [ ] `X-Backend` header identifies which backend served the request
