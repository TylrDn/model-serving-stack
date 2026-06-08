# Architecture — model-serving-stack

## Overview
Production LLM serving stack with three interchangeable backends behind a unified OpenAI-compatible gateway.

## Component Flow

```mermaid
graph TD
    Client[Client / LangChain / Agent] -->|OpenAI API| GW[FastAPI Gateway :8080]
    GW --> vLLM[vLLM Server :8000]
    GW --> Triton[Triton Server :8000/:8001]
    GW --> Ray[Ray Serve :8080]
    vLLM --> GPU[GPU Node / CUDA 12+]
    Triton --> GPU
    Ray --> GPU
    DCGM[DCGM Exporter] --> Prom[Prometheus]
    Prom --> Grafana[Grafana Dashboard]
    HPA[K8s HPA] -->|scale on GPU util| vLLM
    DCGM --> HPA
```

## Backends
| Backend | Best For | Throughput | Latency |
|---|---|---|---|
| vLLM | LLM chat, high throughput | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Triton | Multi-framework, ONNX, TRT | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Ray Serve | Autoscaling, multi-model | ⭐⭐⭐⭐ | ⭐⭐⭐ |

## Autoscaling
HPA watches `dcgm_gpu_utilization` via Prometheus adapter. Scales vLLM pods when GPU util exceeds 80%.
