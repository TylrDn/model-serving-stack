"""Triton Python backend wrapper for LLaMA 3 via vLLM."""
import json
import numpy as np
import triton_python_backend_utils as pb_utils
from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams
import asyncio


class TritonPythonModel:
    def initialize(self, args):
        model_config = json.loads(args["model_config"])
        engine_args = AsyncEngineArgs(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            dtype="float16",
            gpu_memory_utilization=0.90,
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.loop = asyncio.get_event_loop()

    async def _generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
        sampling_params = SamplingParams(temperature=temperature, max_tokens=max_tokens)
        request_id = str(id(prompt))
        results_generator = self.engine.generate(prompt, sampling_params, request_id)
        final_output = None
        async for request_output in results_generator:
            final_output = request_output
        return final_output.outputs[0].text if final_output else ""

    def execute(self, requests):
        responses = []
        for request in requests:
            prompt = pb_utils.get_input_tensor_by_name(request, "text_input").as_numpy()[0].decode("utf-8")
            max_tokens = int(pb_utils.get_input_tensor_by_name(request, "max_tokens").as_numpy()[0]) if pb_utils.get_input_tensor_by_name(request, "max_tokens") else 512
            temperature = float(pb_utils.get_input_tensor_by_name(request, "temperature").as_numpy()[0]) if pb_utils.get_input_tensor_by_name(request, "temperature") else 0.7
            output_text = self.loop.run_until_complete(self._generate(prompt, max_tokens, temperature))
            output_tensor = pb_utils.Tensor("text_output", np.array([output_text.encode()], dtype=object))
            responses.append(pb_utils.InferenceResponse(output_tensors=[output_tensor]))
        return responses

    def finalize(self):
        pass
