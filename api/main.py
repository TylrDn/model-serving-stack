"""OpenAI-compatible FastAPI gateway."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vllm.client import VLLMClient
import uvicorn

app = FastAPI(title="model-serving-stack", version="0.1.0")
client = VLLMClient()


class ChatRequest(BaseModel):
    model: str = "meta/llama3-8b-instruct"
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: int = 512


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        response = client.chat(
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return {
            "choices": [{"message": {"role": "assistant", "content": response}}]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "vllm_ready": client.health_check()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
