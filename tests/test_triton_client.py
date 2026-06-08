"""Unit tests for Triton client."""
import pytest
from unittest.mock import MagicMock, patch


def test_triton_client_health_false_on_error():
    """health_check returns False when server unreachable."""
    with patch("tritonclient.http.InferenceServerClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_server_ready.side_effect = Exception("connection refused")
        mock_cls.return_value = mock_instance
        from triton.client import TritonClient
        tc = TritonClient(url="localhost:9999", protocol="http")
        assert tc.health_check() is False
