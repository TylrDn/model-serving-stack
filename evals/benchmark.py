"""Latency and throughput benchmarking suite."""
import time
import asyncio
import httpx
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    total_requests: int
    successful: int
    failed: int
    avg_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float


async def run_benchmark(
    endpoint: str = "http://localhost:8080/v1/chat/completions",
    num_requests: int = 100,
    concurrency: int = 10,
    prompt: str = "What is machine learning?",
) -> BenchmarkResult:
    latencies = []
    failed = 0
    payload = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 128}

    async def send_request(client: httpx.AsyncClient):
        nonlocal failed
        start = time.monotonic()
        try:
            r = await client.post(endpoint, json=payload, timeout=60.0)
            r.raise_for_status()
            latencies.append((time.monotonic() - start) * 1000)
        except Exception:
            failed += 1

    start_total = time.monotonic()
    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(concurrency)
        async def bounded(c):
            async with sem:
                await send_request(c)
        await asyncio.gather(*[bounded(client) for _ in range(num_requests)])
    elapsed = time.monotonic() - start_total

    latencies.sort()
    return BenchmarkResult(
        total_requests=num_requests,
        successful=len(latencies),
        failed=failed,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
        p99_latency_ms=latencies[int(0.99 * len(latencies))] if latencies else 0,
        throughput_rps=len(latencies) / elapsed,
    )


if __name__ == "__main__":
    result = asyncio.run(run_benchmark())
    print(f"Throughput: {result.throughput_rps:.2f} req/s")
    print(f"Avg Latency: {result.avg_latency_ms:.1f}ms")
    print(f"P99 Latency: {result.p99_latency_ms:.1f}ms")
    print(f"Failed: {result.failed}/{result.total_requests}")
