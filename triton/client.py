"""Triton HTTP/gRPC client wrapper."""
from __future__ import annotations
import numpy as np
from typing import Optional

try:
    import tritonclient.http as httpclient
    import tritonclient.grpc as grpcclient
except ImportError:
    httpclient = None
    grpcclient = None


class TritonClient:
    """Unified HTTP + gRPC client for Triton Inference Server."""

    def __init__(self, url: str = "localhost:8000", protocol: str = "http"):
        self.url = url
        self.protocol = protocol
        if protocol == "grpc":
            self.client = grpcclient.InferenceServerClient(url=url)
        else:
            self.client = httpclient.InferenceServerClient(url=url)

    def health_check(self) -> bool:
        try:
            return self.client.is_server_ready()
        except Exception:
            return False

    def infer(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        if self.protocol == "grpc":
            text_input = grpcclient.InferInput("text_input", [1], "BYTES")
            text_input.set_data_from_numpy(np.array([prompt.encode()], dtype=object))
            output = grpcclient.InferRequestedOutput("text_output")
            result = self.client.infer(model_name, [text_input], outputs=[output])
        else:
            text_input = httpclient.InferInput("text_input", [1], "BYTES")
            text_input.set_data_from_numpy(np.array([prompt.encode()], dtype=object))
            output = httpclient.InferRequestedOutput("text_output")
            result = self.client.infer(model_name, [text_input], outputs=[output])
        return result.as_numpy("text_output")[0].decode("utf-8")
