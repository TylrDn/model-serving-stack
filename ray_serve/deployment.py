"""Ray Serve LLM deployment class."""
from __future__ import annotations
import os
from ray import serve
from vllm import LLM, SamplingParams
from pydantic import BaseModel
from fastapi import FastAPI

app = FastAPI()


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7


@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_gpus": 1},
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 4,
        "target_num_ongoing_requests_per_replica": 8,
    },
)
@serve.ingress(app)
class LLMDeployment:
    def __init__(self):
        model_name = os.getenv("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
        self.llm = LLM(model=model_name, dtype="float16")

    @app.post("/generate")
    def generate(self, request: GenerateRequest) -> dict:
        sampling_params = SamplingParams(temperature=request.temperature, max_tokens=request.max_tokens)
        outputs = self.llm.generate([request.prompt], sampling_params)
        return {"text": outputs[0].outputs[0].text}

    @app.get("/health")
    def health(self) -> dict:
        return {"status": "ok"}


entrypoint = LLMDeployment.bind()
