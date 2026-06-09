"""Tests for load testing utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from evals.benchmark import BenchmarkResult
from evals.load_test import build_report, run_load_test, save_report


def test_build_report_maps_benchmark_fields() -> None:
    result = BenchmarkResult(
        total_requests=10,
        successful=9,
        failed=1,
        avg_latency_ms=12.5,
        p99_latency_ms=20.0,
        throughput_rps=4.2,
    )
    report = build_report(result, endpoint="http://test", concurrency=2)
    assert report.successful == 9
    assert report.throughput_rps == 4.2


def test_save_report_writes_json(tmp_path) -> None:
    result = BenchmarkResult(5, 5, 0, 10.0, 12.0, 3.0)
    report = build_report(result, endpoint="http://test", concurrency=1)
    path = save_report(report, str(tmp_path))
    assert path.exists()
    assert "throughput_rps" in path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_run_load_test_delegates_to_benchmark() -> None:
    mock_result = BenchmarkResult(3, 3, 0, 1.0, 2.0, 5.0)
    with patch("evals.load_test.run_benchmark", new=AsyncMock(return_value=mock_result)):
        report = await run_load_test("http://test", 3, 1, "hello")
    assert report.num_requests == 3
