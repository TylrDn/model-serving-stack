"""Multi-model router for A/B routing across model deployments."""
from __future__ import annotations
import os
import random
from ray import serve
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Multi-Model Router")


class RouteRequest(BaseModel):
    prompt: str
    model: Optional[str] = None  # If None, routes by traffic split
    max_tokens: int = 512
    temperature: float = 0.7


# Traffic split config: model_name -> weight (must sum to 1.0)
TRAFFIC_SPLIT = {
    "llama3-8b": 0.8,
    "llama3-70b": 0.2,
}


def select_model(requested: Optional[str]) -> str:
    if requested and requested in TRAFFIC_SPLIT:
        return requested
    r = random.random()
    cumulative = 0.0
    for model, weight in TRAFFIC_SPLIT.items():
        cumulative += weight
        if r <= cumulative:
            return model
    return list(TRAFFIC_SPLIT.keys())[0]


@serve.deployment(num_replicas=1)
@serve.ingress(app)
class MultiModelRouter:
    def __init__(self, llama3_8b_handle, llama3_70b_handle):
        self.handles = {
            "llama3-8b": llama3_8b_handle,
            "llama3-70b": llama3_70b_handle,
        }

    @app.post("/route")
    async def route(self, request: RouteRequest) -> dict:
        model = select_model(request.model)
        handle = self.handles[model]
        result = await handle.generate.remote(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        return {"model_used": model, "text": result["text"]}
