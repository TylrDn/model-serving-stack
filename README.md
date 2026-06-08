# model-serving-stack

Production LLM serving infrastructure using Triton Inference Server, vLLM, and Ray Serve with OpenAI-compatible endpoints. Includes Kubernetes autoscaling driven by DCGM GPU metrics and a BentoML packaging path for portable model deployment.

**Target Role:** [Solutions Architect, Agentic AI — NVIDIA JR2014517](https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Solutions-Architect--Agentic-AI_JR2014517) | LLM Model Builder JR2014441580

## Architecture

```
model-serving-stack/
├── triton/                    # NVIDIA Triton Inference Server
│   ├── model_repository/      # Triton model configs (config.pbtxt)
│   ├── client.py              # HTTP/gRPC client wrapper
│   └── perf_analyzer.sh       # Triton perf_analyzer benchmark script
├── vllm/                      # vLLM OpenAI-compatible server
│   ├── server.py
│   ├── openai_server.py
│   ├── batching_config.yaml
│   └── client_test.py
├── ray_serve/                 # Ray Serve multi-model router
│   ├── deployment.py
│   ├── autoscaling_config.yaml
│   └── multi_model_router.py
├── bentoml/                   # BentoML packaging path
│   ├── service.py
│   ├── bentofile.yaml
│   └── build_and_push.sh
├── kubernetes/                # K8s manifests + DCGM HPA
├── monitoring/                # Prometheus + Grafana GPU dashboard
├── configs/models.yaml
├── docker-compose.yml
└── README.md
```

## Quick Start

```bash
cp .env.template .env
# Edit .env with your model paths and API keys
docker-compose up
```

## Key Features

- **Triton** — NVIDIA-native inference server with Python backend and ensemble pipeline support
- **vLLM** — OpenAI `/v1/chat/completions` compatible; continuous batching + tensor parallelism
- **DCGM HPA** — Kubernetes autoscaling on GPU utilization (not CPU) — enterprise production pattern
- **Ray Serve** — Multi-model A/B routing and replica autoscaling
- **Grafana Dashboard** — TTFT, tokens/sec, GPU memory, queue depth
- **BentoML** — Portable bento packaging for cross-cloud deployment

## Deployment Target

This repo is the deployment target for models exported from [`llm-finetuning-lab`](https://github.com/TylrDn/llm-finetuning-lab) and benchmarked in [`inference-optimization-bench`](https://github.com/TylrDn/inference-optimization-bench).

## Topics

`triton-inference-server` `vllm` `ray-serve` `bentoml` `llm-serving` `kubernetes` `nvidia` `dcgm` `openai-api` `python` `gpu`
