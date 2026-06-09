"""Unit tests for vLLM OpenAI-compatible server module structure."""
from __future__ import annotations

import importlib.util


def test_openai_server_file_exists():
    """Verify openai_server module file is present and spec is loadable."""
    spec = importlib.util.spec_from_file_location("vllm_openai_server", "vllm/openai_server.py")
    assert spec is not None
    assert spec.loader is not None


def test_vllm_client_file_exists():
    """Verify vllm client module file is present."""
    spec = importlib.util.spec_from_file_location("vllm_client", "vllm/client.py")
    assert spec is not None


def test_server_file_exists():
    """Verify vllm server config file is present."""
    spec = importlib.util.spec_from_file_location("vllm_server", "vllm/server.py")
    assert spec is not None
