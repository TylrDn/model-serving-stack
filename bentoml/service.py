"""BentoML LLM service definition."""
from __future__ import annotations
import os
from typing import Generator
import bentoml
from pydantic import BaseModel

MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7


@bentoml.service(
    resources={"gpu": 1, "memory": "16Gi"},
    traffic={"timeout": 120},
)
class LLMService:
    def __init__(self):
        from vllm import LLM, SamplingParams
        self.llm = LLM(model=MODEL_NAME, dtype="float16")
        self.SamplingParams = SamplingParams

    @bentoml.api
    def generate(self, request: GenerateRequest) -> dict:
        params = self.SamplingParams(temperature=request.temperature, max_tokens=request.max_tokens)
        outputs = self.llm.generate([request.prompt], params)
        return {"text": outputs[0].outputs[0].text, "model": MODEL_NAME}
