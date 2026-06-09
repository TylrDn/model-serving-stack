"""Unit tests for FastAPI gateway."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    with patch("api.main.client") as mock_client:
        mock_client.health_check.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_chat_completions():
    with patch("api.main.client") as mock_client:
        mock_client.chat.return_value = "Machine learning is..."
        response = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "What is ML?"}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["object"] == "chat.completion"
        assert body["choices"][0]["message"]["content"] == "Machine learning is..."
        assert "X-Request-ID" in response.headers


def test_list_models():
    response = client.get("/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    assert len(body["data"]) >= 1
