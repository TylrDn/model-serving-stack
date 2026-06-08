"""BentoML service for portable model packaging."""
import bentoml
from bentoml.io import JSON
from vllm.client import VLLMClient


llm_runner = bentoml.Runner(VLLMClient, name="vllm_runner")
svc = bentoml.Service("llm_service", runners=[llm_runner])


@svc.api(input=JSON(), output=JSON())
def chat(input_data: dict) -> dict:
    messages = input_data.get("messages", [])
    response = llm_runner.chat.run(messages)
    return {"response": response}
