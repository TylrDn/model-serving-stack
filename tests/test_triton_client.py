"""Unit tests for Triton client."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock


def _make_tritonclient_mock():
    """Build a fake tritonclient module tree so TritonClient can be imported without GPU deps."""
    tc_mock = ModuleType("tritonclient")
    tc_http = ModuleType("tritonclient.http")
    tc_grpc = ModuleType("tritonclient.grpc")
    tc_mock.http = tc_http
    tc_mock.grpc = tc_grpc
    tc_http.InferenceServerClient = MagicMock()
    tc_grpc.InferenceServerClient = MagicMock()
    sys.modules.setdefault("tritonclient", tc_mock)
    sys.modules.setdefault("tritonclient.http", tc_http)
    sys.modules.setdefault("tritonclient.grpc", tc_grpc)
    return tc_http, tc_grpc


def test_triton_client_health_false_on_error():
    """health_check returns False when server raises on is_server_ready."""
    tc_http, _ = _make_tritonclient_mock()
    from triton.client import TritonClient

    mock_instance = MagicMock()
    mock_instance.is_server_ready.side_effect = Exception("connection refused")
    tc_http.InferenceServerClient.return_value = mock_instance

    tc = TritonClient(url="localhost:9999", protocol="http")
    tc._client = mock_instance
    assert tc.health_check() is False


def test_triton_client_health_true():
    """health_check returns True when server is ready."""
    tc_http, _ = _make_tritonclient_mock()
    from triton.client import TritonClient

    mock_instance = MagicMock()
    mock_instance.is_server_ready.return_value = True
    tc_http.InferenceServerClient.return_value = mock_instance

    tc = TritonClient(url="localhost:8000", protocol="http")
    tc._client = mock_instance
    assert tc.health_check() is True
