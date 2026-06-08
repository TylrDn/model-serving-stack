"""vLLM AsyncLLMEngine server with FastAPI."""
from __future__ import annotations
import asyncio
import os
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams

app = FastAPI(title="vLLM Server")

engine_args = AsyncEngineArgs(
    model=os.getenv("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct"),
    dtype="float16",
    tensor_parallel_size=int(os.getenv("VLLM_TENSOR_PARALLEL_SIZE", "1")),
    gpu_memory_utilization=0.90,
    max_model_len=8192,
)
engine = AsyncLLMEngine.from_engine_args(engine_args)


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    stream: bool = False


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate(request: GenerateRequest):
    sampling_params = SamplingParams(temperature=request.temperature, max_tokens=request.max_tokens)
    request_id = str(id(request))

    async def stream_results() -> AsyncGenerator[str, None]:
        async for output in engine.generate(request.prompt, sampling_params, request_id):
            yield output.outputs[0].text

    if request.stream:
        return StreamingResponse(stream_results(), media_type="text/plain")
    results = []
    async for output in engine.generate(request.prompt, sampling_params, request_id):
        results.append(output.outputs[0].text)
    return {"text": results[-1] if results else ""}
