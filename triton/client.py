"""Triton HTTP/gRPC client wrapper."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class TritonClient:
    def __init__(self, url: str | None = None, protocol: str = "http"):
        host = os.getenv("TRITON_HOST", "localhost")
        port = (
            os.getenv("TRITON_HTTP_PORT", "8000")
            if protocol == "http"
            else os.getenv("TRITON_GRPC_PORT", "8001")
        )
        self.url = url or f"{host}:{port}"
        self.protocol = protocol
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.protocol == "http":
                import tritonclient.http as httpclient  # noqa: PLC0415
                self._client = httpclient.InferenceServerClient(url=self.url)
            else:
                import tritonclient.grpc as grpcclient  # noqa: PLC0415
                self._client = grpcclient.InferenceServerClient(url=self.url)
        return self._client

    def health_check(self) -> bool:
        try:
            return self._get_client().is_server_ready()
        except Exception:
            return False

    def list_models(self) -> list:
        return self._get_client().get_model_repository_index()

    def infer(self, model_name: str, inputs: list, outputs: list):
        return self._get_client().infer(model_name=model_name, inputs=inputs, outputs=outputs)
