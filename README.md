# Canteen Menu Planner

Generates a week of canteen mains (Mon–Fri, meat + vegetarian) from a product catalogue, grounded in real products and validated. Simple FastAPI web UI.

>Made just for Google and Anthropic models

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put your key in `.env` and pick a provider:

```
LLM_PROVIDER=anthropic        # or gemini
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

## Run

```bash
uvicorn main:app --reload                  # real model
USE_FAKE_LLM=1 uvicorn main:app --reload   # no API cost
```

Open http://127.0.0.1:8000.

## Tests

```bash
pip install pytest httpx
pytest
```

This will run unit tests for validation and summarization logic, as well as integration tests for the API endpoints (fixed to use the fake LLM to avoid costs).
