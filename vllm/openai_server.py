"""OpenAI-compatible /v1/chat/completions endpoint backed by vLLM."""
from __future__ import annotations

import os
import time
import uuid
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams

app = FastAPI(title="vLLM OpenAI-Compatible Server")

engine_args = AsyncEngineArgs(
    model=os.getenv("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct"),
    dtype="float16",
    tensor_parallel_size=int(os.getenv("VLLM_TENSOR_PARALLEL_SIZE", "1")),
)
engine = AsyncLLMEngine.from_engine_args(engine_args)
MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "llama3")


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_NAME
    messages: List[Message]
    max_tokens: int = 512
    temperature: float = 0.7
    stream: bool = False


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages) + "\nassistant:"
    sampling_params = SamplingParams(temperature=request.temperature, max_tokens=request.max_tokens)
    request_id = str(uuid.uuid4())
    results = []
    async for output in engine.generate(prompt, sampling_params, request_id):
        results.append(output.outputs[0].text)
    text = results[-1] if results else ""
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            },
        ],
    }
