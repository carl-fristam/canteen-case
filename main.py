"""FastAPI app: serves the page plus the /plan and /plan/stream endpoints."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

import anthropic
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import ValidationError

from config import USE_FAKE_LLM, PROVIDER
from data.product_store import ProductStore
from llm.prompt import SYSTEM, format_catalogue
from llm.fake_planner import fake_plan_week
from services.validate import validate_plan
from services.summarize import summarize_plan
from schemas import WeeklyPlan, Product, PromptView, PlanResponse


# Setup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("canteen")

INDEX = Path(__file__).parent / "frontend" / "index.html"
ALLERGENS = ("gluten", "nuts", "dairy")
PREVIEW_ROWS = 20        # catalogue rows shown in the UI's "what the AI saw" panel


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the product catalogue into memory once, and keep it for the app's lifetime.
    app.state.store = ProductStore()
    log.info("loaded store: %d available products | fake_llm=%s",
             len(app.state.store.candidates()), USE_FAKE_LLM)
    yield


app = FastAPI(title="Canteen Menu Planner", lifespan=lifespan)


# Planning

def _norm_exclude(exclude: list[str]) -> frozenset[str]:
    """Keep only recognised allergen names from the query string."""
    return frozenset(a for a in exclude if a in ALLERGENS)


def _planner():
    """Lazily import the selected provider — only the chosen client is constructed."""
    if PROVIDER == "gemini":
        from llm.gemini_planner import plan_week
    else:
        from llm.anthropic_planner import plan_week
    return plan_week


def _make_plan(products: list[Product], catalogue: str,
               on_thought: Callable[[str], None] | None = None) -> WeeklyPlan:
    """Build a plan from the rendered candidates, failing early when a track is empty.

    on_thought, if given, receives the model's reasoning text as it streams.
    """
    if not any(p.dietary_class == "meat" for p in products):
        raise RuntimeError("No meat-track products available for the selected filters.")
    if sum(p.dietary_class in ("vegan", "vegetarian") for p in products) < 2:
        raise RuntimeError("Not enough vegetarian products available for the selected filters.")
    if USE_FAKE_LLM:
        return fake_plan_week(products)
    return _planner()(catalogue, on_thought)


def _prompt_view(catalogue: str, count: int) -> PromptView:
    """The grounding text shown in the UI's 'what the AI saw' panel."""
    preview = "\n".join(catalogue.split("\n")[:1 + PREVIEW_ROWS])   # header + N rows
    return PromptView(system=SYSTEM, catalogue_count=count, catalogue_preview=preview)


def _err_detail(e: Exception) -> str:
    """Turn an exception into a short, user-facing message."""
    if isinstance(e, anthropic.APIError):
        body = getattr(e, "body", None)
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            if msg := body["error"].get("message"):
                return f"LLM error: {msg}"
        return f"LLM error: {getattr(e, 'message', str(e))}"
    if isinstance(e, ValidationError):
        return "LLM returned a malformed plan"
    if msg := getattr(e, "message", None):      # e.g. google-genai APIError
        return f"LLM error: {msg}"
    return str(e)


# Routes

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX.read_text()


@app.get("/health")
def health():
    return {"status": "ok", "fake_llm": USE_FAKE_LLM}


@app.post("/plan", response_model=PlanResponse)
def plan(exclude: list[str] = Query(default=[])):
    store = app.state.store
    exclude_set = _norm_exclude(exclude)
    products = store.candidates(exclude_set)
    catalogue = format_catalogue(products)
    try:
        weekly = _make_plan(products, catalogue)
    except Exception as e:
        log.error("plan failed: %s", e)
        raise HTTPException(status_code=502, detail=_err_detail(e))

    checks = validate_plan(weekly, store, exclude_set)
    if not all(c.passed for c in checks):
        fails = [d for c in checks if not c.passed for d in c.details]
        raise HTTPException(status_code=502, detail=f"Validation failed: {'; '.join(fails[:3])}...")

    summary = summarize_plan(weekly, store)
    log.info("plan generated and validated")
    return PlanResponse(valid=True, checks=checks, plan=weekly, summary=summary,
                        prompt=_prompt_view(catalogue, len(products)))


def _sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/plan/stream")
async def plan_stream(exclude: list[str] = Query(default=[])):
    store = app.state.store
    exclude_set = _norm_exclude(exclude)
    products = store.candidates(exclude_set)
    catalogue = format_catalogue(products)
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    # The blocking planner runs in a worker thread; bridge its output back to the event loop.
    def on_thought(text: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ("thinking", text))

    def work() -> None:
        try:
            weekly = _make_plan(products, catalogue, on_thought)
            loop.call_soon_threadsafe(queue.put_nowait, ("result", weekly))
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", e))

    async def gen():
        loop.run_in_executor(None, work)
        while True:
            kind, payload = await queue.get()

            # Stream the model's reasoning as it arrives.
            if kind == "thinking":
                yield _sse("thinking", {"text": payload})
                continue

            if kind == "error":
                log.error("stream plan failed: %s", payload)
                yield _sse("failed", {"detail": _err_detail(payload)})
                return

            # kind == "result": validate, summarize, and send the finished plan.
            weekly = payload
            checks = validate_plan(weekly, store, exclude_set)
            if not all(c.passed for c in checks):
                fails = [d for c in checks if not c.passed for d in c.details]
                yield _sse("failed", {"detail": f"Validation failed: {'; '.join(fails[:2])}"})
                return

            summary = summarize_plan(weekly, store)
            log.info("plan generated and validated")
            yield _sse("done", {
                "valid": True,
                "checks": [c.model_dump() for c in checks],
                "plan": weekly.model_dump(),
                "summary": summary.model_dump(),
                "prompt": _prompt_view(catalogue, len(products)).model_dump(),
            })
            return

    return StreamingResponse(gen(), media_type="text/event-stream")
