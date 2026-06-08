---
name: run-load-test
description: Invoke when setting up or running load tests against the serving stack. Use when the user asks to run locust load tests, benchmark API throughput, compare backend performance under load, or generate load test reports.
model: inherit
readonly: false
is_background: false
---

# Run Load Test Against Model Serving Stack

## Objective

Update `evals/benchmark.py` with a production locust-based load test that hits the FastAPI gateway, supports configurable backends (vllm/triton/ray/bento), measures P50/P95/P99 latency and throughput, and generates a summary report. Also create a `locustfile.py` for interactive or headless locust runs.

---

## Files to Create / Modify

### Modify: `evals/benchmark.py`

Replace or extend with a full load test orchestrator.

**Imports:**
```python
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Any

import httpx

logger = logging.getLogger(__name__)
```

**`BenchmarkConfig` dataclass:**
```python
@dataclass
class BenchmarkConfig:
    base_url: str = "http://localhost:8000"
    backend: str = "vllm"               # vllm | triton | ray | bento
    model: str = "meta/llama3-8b-instruct"
    num_users: int = 10                  # concurrent virtual users
    spawn_rate: int = 2                  # users/second ramp rate
    run_time_seconds: int = 60
    prompt_length: str = "short"         # short | medium | long
    output_dir: Path = Path("results/load_tests")
    use_locust: bool = True              # True=locust, False=httpx direct
```

**`BenchmarkResult` dataclass:**
```python
@dataclass
class BenchmarkResult:
    run_id: str
    timestamp: str
    config: dict[str, Any]
    total_requests: int
    failed_requests: int
    requests_per_second: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_max_ms: float
    ttft_p50_ms: float | None           # Time to first token (if streaming)
    ttft_p95_ms: float | None
    error_rate: float                   # failed / total
    results_path: Path
```

**`run_httpx_benchmark(config: BenchmarkConfig) -> BenchmarkResult`:**

Direct HTTPX load test (no locust dependency):
```python
async def _single_request(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    prompt: str,
) -> dict[str, float]:
    """Send a single chat completion request and measure latency."""
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": 0.7,
        "backend": config.backend,
        "stream": False,
    }
    t_start = time.perf_counter()
    try:
        response = await client.post("/v1/chat/completions", json=payload, timeout=30.0)
        latency_ms = (time.perf_counter() - t_start) * 1000
        return {
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "tokens": response.json().get("usage", {}).get("completion_tokens", 0),
        }
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        latency_ms = (time.perf_counter() - t_start) * 1000
        return {"latency_ms": latency_ms, "status_code": 0, "success": False, "tokens": 0}
```

Orchestration:
1. Generate `n_requests = config.num_users * config.run_time_seconds // 5` prompts from `PROMPT_TEMPLATES[config.prompt_length]`
2. Use `asyncio.gather()` with concurrency limiter (`asyncio.Semaphore(config.num_users)`)
3. Collect all `dict[str, float]` results
4. Compute percentiles using `statistics.quantiles(latencies, n=100)` — P50 = index 49, P95 = index 94, P99 = index 98
5. Compute `requests_per_second = total_requests / config.run_time_seconds`
6. Save results JSON and return `BenchmarkResult`

**Prompt templates:**
```python
PROMPT_TEMPLATES: dict[str, list[str]] = {
    "short": [
        "What is 2 + 2?",
        "Name a planet in our solar system.",
        "What color is the sky?",
        "Say hello.",
        "What year is it?",
    ],
    "medium": [
        "Explain the concept of gradient descent in 3 sentences.",
        "What are the main differences between TCP and UDP protocols?",
        "Describe the water cycle briefly.",
        "What is transfer learning in machine learning?",
        "Explain why GPUs are used for AI training.",
    ],
    "long": [
        "Write a detailed explanation of how transformer attention mechanisms work, covering self-attention, multi-head attention, and positional encoding.",
        "Compare and contrast supervised learning, unsupervised learning, and reinforcement learning with examples of each.",
        "Explain the NVIDIA NIM platform: what it is, how it differs from running vLLM directly, and what use cases it's optimized for.",
        "Describe the complete process of fine-tuning a large language model from data preparation through deployment, covering key decisions at each step.",
        "What are the key architectural differences between GPT-style autoregressive models and BERT-style bidirectional models?",
    ],
}
```

**`run_locust_benchmark(config: BenchmarkConfig) -> BenchmarkResult`:**

Run locust headlessly via subprocess:
```python
def run_locust_benchmark(config: BenchmarkConfig) -> BenchmarkResult:
    """Run locust in headless mode and parse results CSV."""
    csv_prefix = str(config.output_dir / f"locust_{config.backend}_{int(time.time())}")
    
    cmd = [
        sys.executable, "-m", "locust",
        "--headless",
        "--users", str(config.num_users),
        "--spawn-rate", str(config.spawn_rate),
        "--run-time", f"{config.run_time_seconds}s",
        "--host", config.base_url,
        "--csv", csv_prefix,
        "--locustfile", "evals/locustfile.py",
        "--exit-code-on-error", "0",
        f"--backend={config.backend}",
        f"--model={config.model}",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):  # locust exits 1 if any failures (acceptable)
        raise EvalError(f"Locust failed:\n{result.stderr}")
    
    # Parse CSV results
    return _parse_locust_csv(csv_prefix + "_stats.csv", config)
```

**`generate_load_test_report(result: BenchmarkResult, output_dir: Path) -> Path`:**

Generate markdown summary:
```markdown
# Load Test Report

**Backend:** {backend}  
**Model:** {model}  
**Run Time:** {run_time_seconds}s  
**Concurrent Users:** {num_users}

## Results

| Metric | Value |
|--------|-------|
| Requests/sec | {rps:.1f} |
| Latency P50 | {p50:.1f} ms |
| Latency P95 | {p95:.1f} ms |
| Latency P99 | {p99:.1f} ms |
| Max Latency | {max:.1f} ms |
| Error Rate | {error_rate:.1%} |
| Total Requests | {total} |
| Failed Requests | {failed} |
```

---

### Create: `evals/locustfile.py`

Full locust load test definition:

```python
from __future__ import annotations

import json
import random
from locust import HttpUser, between, task
from locust import events

class LLMServingUser(HttpUser):
    """Simulates a user sending chat completion requests to the serving stack."""
    
    wait_time = between(0.1, 1.0)
    
    def on_start(self) -> None:
        # Get backend/model from environment (set by run_locust_benchmark)
        self.backend = os.environ.get("LOCUST_BACKEND", "vllm")
        self.model = os.environ.get("LOCUST_MODEL", "meta/llama3-8b-instruct")
        self.prompts = PROMPT_TEMPLATES["medium"]  # import from benchmark.py
    
    @task(3)
    def short_completion(self) -> None:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": random.choice(PROMPT_TEMPLATES["short"])}],
            "max_tokens": 64,
            "backend": self.backend,
        }
        with self.client.post(
            "/v1/chat/completions",
            json=payload,
            catch_response=True,
            name="/v1/chat/completions (short)",
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def medium_completion(self) -> None:
        # Same pattern, medium prompts, max_tokens=256
        ...
    
    @task(1)
    def long_completion(self) -> None:
        # Same pattern, long prompts, max_tokens=512
        ...
    
    @task(1)
    def health_check(self) -> None:
        self.client.get("/health", name="/health")
```

---

### Create: `tests/test_benchmark.py`

```python
def test_benchmark_config_defaults(): ...
def test_benchmark_result_schema(): ...
async def test_run_httpx_benchmark_short(mock_httpx_client): ...
async def test_run_httpx_benchmark_all_fail(mock_httpx_client): ...
def test_generate_report_creates_markdown(mock_result, tmp_path): ...
def test_percentile_calculation(): ...

@pytest.mark.parametrize("prompt_length", ["short", "medium", "long"])
def test_prompt_templates_nonempty(prompt_length): ...
```

---

## CLI

```bash
# Run quick benchmark (30s, 5 users, httpx mode)
python evals/benchmark.py --backend vllm --model meta/llama3-8b-instruct \
  --users 5 --run-time 30 --no-locust

# Run full locust benchmark
python evals/benchmark.py --backend vllm --users 20 --run-time 120

# Compare all backends
python evals/benchmark.py --compare-all --model meta/llama3-8b-instruct
```

---

## Acceptance Criteria

- [ ] `python evals/benchmark.py --backend vllm --users 5 --run-time 30 --no-locust` runs against live API
- [ ] `python evals/benchmark.py --backend vllm --users 10 --run-time 60` runs locust headlessly
- [ ] `BenchmarkResult` JSON written to `results/load_tests/`
- [ ] Markdown report generated with latency percentile table
- [ ] `pytest tests/test_benchmark.py` passes (mock httpx)
- [ ] `mypy --strict evals/benchmark.py` exits 0
- [ ] `ruff check evals/benchmark.py` exits 0
- [ ] P95 and P99 are computed correctly from sample data
- [ ] Error rate is `failed_requests / total_requests`
- [ ] `locustfile.py` imports without errors when locust is installed
