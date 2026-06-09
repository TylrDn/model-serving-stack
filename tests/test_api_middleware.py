"""Tests for structured API logging middleware."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_is_not_logged_with_request_id() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" not in response.headers


def test_chat_request_includes_request_id_and_backend_header() -> None:
    with patch("api.main.client") as mock_client:
        mock_client.chat.return_value = "ok"
        response = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
    assert response.status_code == 200
    assert response.headers.get("X-Backend") == "vllm"
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert len(request_id) == 36
