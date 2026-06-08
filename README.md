# model-serving-stack

Production LLM serving infrastructure using Triton Inference Server, vLLM, and Ray Serve with OpenAI-compatible endpoints. Includes DCGM GPU autoscaling, Grafana monitoring, and BentoML packaging.

## Stack
- **Triton Inference Server** — multi-framework model serving
- **vLLM** — high-throughput LLM serving with PagedAttention
- **Ray Serve** — scalable model deployment with autoscaling
- **BentoML** — portable model packaging and deployment
- **DCGM** — GPU metrics and autoscaling signals

## Structure
```
model-serving-stack/
├── triton/              # Triton model repo + config
├── vllm/               # vLLM server configs and scripts
├── ray_serve/          # Ray Serve deployment definitions
├── bentoml/            # BentoML service and packaging
├── autoscaling/        # HPA manifests driven by DCGM metrics
├── monitoring/         # Grafana dashboards + Prometheus rules
├── deploy/             # Docker Compose + Kubernetes manifests
├── api/                # OpenAI-compatible FastAPI gateway
├── configs/            # Model and serving configs
├── evals/              # Latency/throughput benchmarks
├── tests/              # Unit + integration tests
└── docs/               # Architecture docs
```

## Quick Start
```bash
cp .env.template .env
# Fill in NGC_API_KEY, MODEL_PATH, etc.
docker compose -f deploy/docker-compose.yml up
```

## Requirements
- NVIDIA GPU with CUDA 12+
- Docker + NVIDIA Container Toolkit
- Kubernetes (optional, for production)
