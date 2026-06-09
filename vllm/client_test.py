"""Load test client for vLLM OpenAI-compatible server."""
import asyncio
import time

import httpx

BASE_URL = "http://localhost:8000"
CONCURRENCY = 10
NUM_REQUESTS = 100
PROMPT = "Explain the DCGM GPU metrics used for Kubernetes autoscaling in two sentences."


async def single_request(client: httpx.AsyncClient, idx: int) -> dict:
    start = time.perf_counter()
    response = await client.post(
        f"{BASE_URL}/v1/chat/completions",
        json={"messages": [{"role": "user", "content": PROMPT}], "max_tokens": 128},
        timeout=60.0,
    )
    latency = time.perf_counter() - start
    return {"idx": idx, "status": response.status_code, "latency": latency}


async def run_load_test():
    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(CONCURRENCY)
        async def bounded(idx):
            async with sem:
                return await single_request(client, idx)
        results = await asyncio.gather(*[bounded(i) for i in range(NUM_REQUESTS)])
    latencies = [r["latency"] for r in results]
    print(f"Completed {NUM_REQUESTS} requests @ concurrency={CONCURRENCY}")
    print(f"Avg latency: {sum(latencies)/len(latencies):.3f}s")
    print(f"P95 latency: {sorted(latencies)[int(0.95*len(latencies))]:.3f}s")
    print(f"Throughput: {NUM_REQUESTS/sum(latencies)*CONCURRENCY:.2f} req/s")


if __name__ == "__main__":
    asyncio.run(run_load_test())
