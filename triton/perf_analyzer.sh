#!/usr/bin/env bash
# Triton perf_analyzer benchmark script
# Measures latency and throughput for a deployed Triton model

set -euo pipefail

MODEL_NAME=${MODEL_NAME:-"llama3"}
TRITON_URL=${TRITON_URL:-"localhost:8000"}
CONCURRENCY=${CONCURRENCY:-4}
REQUEST_COUNT=${REQUEST_COUNT:-100}

echo "Running perf_analyzer for model: $MODEL_NAME"
echo "URL: $TRITON_URL | Concurrency: $CONCURRENCY | Requests: $REQUEST_COUNT"

perf_analyzer \
  -m "$MODEL_NAME" \
  -u "$TRITON_URL" \
  --concurrency-range "$CONCURRENCY" \
  --measurement-request-count "$REQUEST_COUNT" \
  --percentile=95 \
  --shape text_input:1 \
  -b 1
