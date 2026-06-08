"""Ray Serve LLM deployment with autoscaling."""
from ray import serve
from ray.serve.config import AutoscalingConfig
from vllm.client import VLLMClient
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ChatRequest(BaseModel):
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 512


@serve.deployment(
    autoscaling_config=AutoscalingConfig(
        min_replicas=1,
        max_replicas=4,
        target_num_ongoing_requests_per_replica=8,
    ),
    ray_actor_options={"num_gpus": 1},
)
@serve.ingress(app)
class LLMDeployment:
    def __init__(self):
        self.client = VLLMClient()

    @app.post("/chat")
    async def chat(self, request: ChatRequest) -> dict:
        response = self.client.chat(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return {"response": response}

    @app.get("/health")
    async def health(self) -> dict:
        return {"status": "ok", "vllm_ready": self.client.health_check()}


entrypoint = LLMDeployment.bind()
