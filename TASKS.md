# model-serving-stack — Task Board

**Repo:** model-serving-stack
**Completion:** 95%
**Last Audit:** 2026-06-08
**Open Tasks:** 3 critical / 3 polish / 2 enhancement

---

## Priority 1 — CRITICAL

### [ ] 1.1 Remove Duplicate triton/model_repo/ Directory
**Files:** `triton/model_repo/` (DELETE), plus all files referencing it
**What:** The `triton/model_repo/` directory is a duplicate of the canonical `triton/model_repository/`. Safe removal workflow: (1) audit references with `grep -r "model_repo/"`, (2) verify canonical has superset content, (3) update all references in `triton/client.py`, both `docker-compose.yml` files, `kubernetes/triton-deployment.yaml`, `docs/architecture.md`, (4) remove `triton/model_repo/`, (5) run tests to confirm no breakage.
**Acceptance Criteria:**
- `triton/model_repo/` does not exist
- `grep -r "model_repo/" . | grep -v model_repository | grep -v .git` returns empty
- `docker-compose config` exits 0
- `pytest tests/ -m "not gpu"` still passes
- `triton/client.py` references `triton/model_repository` (not `model_repo`)

---

### [ ] 1.2 Remove Duplicate monitoring/grafana_dashboard.json
**Files:** `monitoring/grafana_dashboard.json` (DELETE), plus all files referencing it
**What:** `monitoring/grafana_dashboard.json` at the repo root is a duplicate of `monitoring/grafana/gpu_serving_dashboard.json` (canonical). Safe removal: (1) diff the two files, merge any differences into canonical, (2) update both `docker-compose.yml` files to use `monitoring/grafana/gpu_serving_dashboard.json`, (3) update any Kubernetes ConfigMap references, (4) remove root duplicate.
**Acceptance Criteria:**
- `monitoring/grafana_dashboard.json` does not exist
- Grafana provisioned from `monitoring/grafana/gpu_serving_dashboard.json`
- Both docker-compose files reference correct path
- Grafana dashboard loads in `docker-compose up` without errors

---

### [ ] 1.3 Add Structured Request/Response Logging Middleware
**File:** `api/main.py`
**What:** Add `StructuredLoggingMiddleware` (Starlette `BaseHTTPMiddleware`) that logs every non-health request as structured JSON: `request_id` (UUID v4), `method`, `path`, `status_code`, `latency_ms` (using `time.perf_counter()`), `client_ip`, `user_agent`, `model` (extracted from request body). Add `X-Request-ID` and `X-Backend` response headers. Add `JSONLogFormatter` for structured log output. Skip `/health` and `/metrics` paths. Update Prometheus counters `api_requests_total` and `api_request_latency_seconds` histogram.
**Acceptance Criteria:**
- Every non-health API response includes `X-Request-ID` header (valid UUID)
- `logger.info("api_request", extra={...})` fires for every request
- `/health` NOT logged
- `api_requests_total` counter visible at `/metrics`
- `pytest tests/test_api_middleware.py` passes
- `mypy --strict api/main.py` exits 0

---

## Priority 2 — POLISH

### [ ] 2.1 Load Test Suite
**Files:** `evals/benchmark.py` (update), `evals/locustfile.py` (create)
**What:** Full load test orchestrator with httpx direct mode and locust headless mode. `BenchmarkConfig` dataclass, `BenchmarkResult` with P50/P95/P99 latency, markdown report generation. Prompt templates for short/medium/long workloads. CLI: `python evals/benchmark.py --backend vllm --users 10 --run-time 60`.
**Acceptance Criteria:**
- `python evals/benchmark.py --no-locust --users 5 --run-time 30` runs against live API
- Results JSON written to `results/load_tests/`
- Markdown report includes latency percentile table
- `pytest tests/test_benchmark.py` passes

### [ ] 2.2 API Schema Polish
**File:** `api/main.py`
**What:** Add OpenAPI descriptions to all route docstrings. Add Pydantic v2 request/response models with field validators. Ensure `/v1/chat/completions` is fully OpenAI-compatible (response schema matches OpenAI API exactly). Add `POST /v1/models` endpoint listing available models from `configs/models.yaml`.
**Acceptance Criteria:**
- `GET /docs` (Swagger UI) renders without errors
- All routes have descriptions in OpenAPI spec
- `/v1/chat/completions` response schema matches OpenAI API format
- `GET /v1/models` returns models from config

### [ ] 2.3 Grafana Dashboard GPU Panels Polish
**File:** `monitoring/grafana/gpu_serving_dashboard.json`
**What:** Add missing panels to GPU serving dashboard: TTFT P95 per backend, tokens/sec per model, error rate, active connections. Ensure all panels use correct DCGM metric names (`DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_MEM_COPY_UTIL`, `DCGM_FI_DEV_FB_USED`).
**Acceptance Criteria:**
- Dashboard JSON validates as valid Grafana JSON model
- At least 6 panels: GPU utilization, memory used, TTFT, throughput, error rate, active connections
- All DCGM metric names are correct
- Dashboard provisioned automatically via ConfigMap in `docker-compose up`

---

## Priority 3 — ENHANCEMENT

### [ ] 3.1 Multi-Backend Health Aggregation
**File:** `api/main.py`
**What:** Enhance `/health` endpoint to return per-backend health status (not just API health). Check vLLM, Triton, Ray Serve, BentoML connectivity. Return aggregated status: `{"status": "degraded", "backends": {"vllm": "healthy", "triton": "unavailable"}}`. Return 200 if any backend healthy, 503 if all backends unavailable.
**Acceptance Criteria:**
- `/health` returns per-backend status dict
- Returns 503 when all backends are down
- Backend health checks have 2s timeout (non-blocking)
- `pytest tests/test_api_middleware.py::test_health_check_aggregated` passes

### [ ] 3.2 Request Rate Limiting
**File:** `api/main.py`
**What:** Add token-bucket rate limiting middleware using `slowapi` or a custom implementation. Configurable: per-IP limit (default 60 req/min), per-model limit, global limit. Return 429 with `Retry-After` header when exceeded. Log rate limit events at WARNING level with `client_ip` and `request_id`.
**Acceptance Criteria:**
- Rapid-fire requests (>60/min from same IP) receive 429
- `Retry-After` header present on 429 responses
- Rate limit events logged with client_ip
- Rate limits configurable via `configs/serving.yaml`
