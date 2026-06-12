# Contributing to model-serving-stack

Thank you for your interest in contributing! This document outlines the development workflow and standards.

## Development Setup

```bash
git clone https://github.com/TylrDn/model-serving-stack.git
cd model-serving-stack
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.template .env  # fill in required values
```

## Code Standards

This repo enforces:
- **`ruff`** — linting and formatting (replaces flake8 + black)
- **`mypy`** — strict type checking
- **`pytest`** — test runner with `--cov-fail-under=80`

Run all checks before submitting a PR:

```bash
ruff check . && mypy . && pytest --cov --cov-fail-under=80
```

## Branch & PR Workflow

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes with focused commits using [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
3. Open a PR against `main` — CI runs automatically
4. All CI checks must be green before merge

## Adding a New Backend

To add a new serving backend (e.g., TensorRT-LLM standalone):

1. Create a directory under the backend name: `tensorrt_llm/`
2. Implement the client following the interface in `api/openai_server.py`
3. Add the backend key to `configs/models.yaml`
4. Add integration tests in `tests/test_<backend>.py`
5. Update the `SERVING_BACKEND` options in `.env.template` and this README

## Testing

```bash
# All tests
pytest

# Specific test file
pytest tests/test_api.py -v

# With coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Load test (requires running server)
locust -f evals/load_test.py --headless -u 32 -r 4 --run-time 60s --host http://localhost:8000
```

## Questions

Open an issue or reach out via the [NVIDIA Solutions Architect portfolio](https://github.com/TylrDn).
