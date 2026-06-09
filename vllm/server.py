"""vLLM OpenAI-compatible server launcher."""
import os
import subprocess

from dotenv import load_dotenv

load_dotenv()


def launch_vllm_server():
    model = os.getenv("MODEL_NAME", "meta/llama3-8b-instruct")
    host = os.getenv("VLLM_HOST", "0.0.0.0")
    port = os.getenv("VLLM_PORT", "8000")
    tp = os.getenv("TENSOR_PARALLEL_SIZE", "1")
    max_len = os.getenv("MAX_MODEL_LEN", "8192")

    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--host", host,
        "--port", port,
        "--tensor-parallel-size", tp,
        "--max-model-len", max_len,
        "--dtype", "bfloat16",
        "--enable-prefix-caching",
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    launch_vllm_server()
