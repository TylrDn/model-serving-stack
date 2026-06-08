"""Triton HTTP/gRPC client wrapper."""
import tritonclient.http as httpclient
from dotenv import load_dotenv
import os

load_dotenv()


class TritonClient:
    def __init__(self, url: str = None):
        host = os.getenv("TRITON_HOST", "localhost")
        port = os.getenv("TRITON_HTTP_PORT", "8000")
        self.url = url or f"{host}:{port}"
        self.client = httpclient.InferenceServerClient(url=self.url)

    def health_check(self) -> bool:
        return self.client.is_server_ready()

    def list_models(self) -> list:
        return self.client.get_model_repository_index()

    def infer(self, model_name: str, inputs: list, outputs: list):
        return self.client.infer(model_name=model_name, inputs=inputs, outputs=outputs)
