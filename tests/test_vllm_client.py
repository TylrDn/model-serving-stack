"""Unit tests for vLLM client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from vllm.client import VLLMClient


def test_health_check_true():
    """health_check returns True when vLLM server has models loaded."""
    with patch("vllm.client.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_instance.models.list.return_value.data = ["model1"]
        mock_openai_cls.return_value = mock_instance
        client = VLLMClient()
        assert client.health_check() is True


def test_health_check_false():
    """health_check returns False when vLLM server is unreachable."""
    with patch("vllm.client.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_instance.models.list.side_effect = Exception("Connection refused")
        mock_openai_cls.return_value = mock_instance
        client = VLLMClient()
        assert client.health_check() is False


def test_chat_returns_content():
    """chat() returns the assistant message content string."""
    with patch("vllm.client.OpenAI") as mock_openai_cls:
        mock_instance = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "The answer is 42."
        mock_instance.chat.completions.create.return_value.choices = [mock_choice]
        mock_openai_cls.return_value = mock_instance
        client = VLLMClient()
        result = client.chat(messages=[{"role": "user", "content": "What is the answer?"}])
        assert result == "The answer is 42."
