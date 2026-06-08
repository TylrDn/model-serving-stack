"""Unit tests for vLLM OpenAI-compatible server."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def test_openai_server_imports():
    """Verify openai_server module structure is importable."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("openai_server", "vllm/openai_server.py")
    assert spec is not None


def test_health_endpoint():
    """Health endpoint returns ok."""
    with patch("vllm.AsyncLLMEngine.from_engine_args"):
        from vllm.openai_server import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
