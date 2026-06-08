#!/usr/bin/env bash
# Build and push BentoML service to BentoCloud
set -euo pipefail

echo "Building Bento..."
bentoml build

echo "Pushing to BentoCloud..."
bentoml push llm-serving:latest

echo "Done. Deploy via: bentoml deploy llm-serving:latest --name model-serving-stack"
