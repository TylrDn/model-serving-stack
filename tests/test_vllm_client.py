"""Unit tests for vLLM client."""
from unittest.mock import MagicMock, patch
from vllm.client import VLLMClient


def test_health_check_true():
    with patch("vllm.client.OpenAI") as MockOpenAI:
        mock_instance = MagicMock()
        mock_instance.models.list.return_value.data = ["model1"]
        MockOpenAI.return_value = mock_instance
        client = VLLMClient()
        assert client.health_check() is True


def test_health_check_false():
    with patch("vllm.client.OpenAI") as MockOpenAI:
        mock_instance = MagicMock()
        mock_instance.models.list.side_effect = Exception("Connection refused")
        MockOpenAI.return_value = mock_instance
        client = VLLMClient()
        assert client.health_check() is False
