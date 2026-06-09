"""Load test helpers and CLI for the serving gateway."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from evals.benchmark import BenchmarkResult, run_benchmark

logger = logging.getLogger(__name__)


@dataclass
class LoadTestReport:
    """Serializable load test summary."""

    endpoint: str
    num_requests: int
    concurrency: int
    successful: int
    failed: int
    avg_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    timestamp: str


def build_report(result: BenchmarkResult, endpoint: str, concurrency: int) -> LoadTestReport:
    """Convert a benchmark result into a load-test report."""
    return LoadTestReport(
        endpoint=endpoint,
        num_requests=result.total_requests,
        concurrency=concurrency,
        successful=result.successful,
        failed=result.failed,
        avg_latency_ms=round(result.avg_latency_ms, 2),
        p99_latency_ms=round(result.p99_latency_ms, 2),
        throughput_rps=round(result.throughput_rps, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def save_report(report: LoadTestReport, output_dir: str) -> Path:
    """Persist load test report as JSON."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"load_test_{report.timestamp.replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    logger.info("Load test report saved to %s", path)
    return path


async def run_load_test(
    endpoint: str,
    num_requests: int,
    concurrency: int,
    prompt: str,
) -> LoadTestReport:
    """Execute async load test and return report."""
    result = await run_benchmark(
        endpoint=endpoint,
        num_requests=num_requests,
        concurrency=concurrency,
        prompt=prompt,
    )
    return build_report(result, endpoint=endpoint, concurrency=concurrency)


def main() -> None:
    """CLI entrypoint for load testing."""
    parser = argparse.ArgumentParser(description="Run load tests against the serving API")
    parser.add_argument("--endpoint", default="http://localhost:8080/v1/chat/completions")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--prompt", default="Explain tensor parallelism briefly.")
    parser.add_argument("--output-dir", default="results/load_tests")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    report = asyncio.run(
        run_load_test(
            endpoint=args.endpoint,
            num_requests=args.requests,
            concurrency=args.concurrency,
            prompt=args.prompt,
        )
    )
    save_report(report, args.output_dir)


if __name__ == "__main__":
    main()
