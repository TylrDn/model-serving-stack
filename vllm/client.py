"""vLLM OpenAI-compatible client."""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class VLLMClient:
    def __init__(self):
        host = os.getenv("VLLM_HOST", "localhost")
        port = os.getenv("VLLM_PORT", "8000")
        self.client = OpenAI(
            base_url=f"http://{host}:{port}/v1",
            api_key="EMPTY"
        )
        self.model = os.getenv("MODEL_NAME", "meta/llama3-8b-instruct")

    def chat(self, messages: list, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

    def health_check(self) -> bool:
        try:
            models = self.client.models.list()
            return len(models.data) > 0
        except Exception:
            return False
