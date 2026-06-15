"""FastAPI app: serves the page, the /plan endpoint, and a streaming variant."""
import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from config import USE_FAKE_LLM, PROVIDER
from data.product_store import ProductStore
from llm.prompt import SYSTEM, format_catalogue
from llm.fake_planner import fake_plan_week
from services.validate import validate_plan
from services.summarize import summarize_plan
from schemas import WeeklyPlan, Check, WeeklySummary, Product

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("canteen")

INDEX = Path(__file__).parent / "frontend" / "index.html"
ALLERGENS = ("gluten", "nuts", "dairy")
SAMPLE_ROWS = 20        # catalogue rows shown in the "what the AI saw" panel


# lifespan hook to have the ProductStore be in memory throughout up-time
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = ProductStore()
    log.info("loaded store: %d available products | fake_llm=%s",
             len(app.state.store.candidates()), USE_FAKE_LLM)
    yield


app = FastAPI(title="Canteen Menu Planner", lifespan=lifespan)


class PromptView(BaseModel):
    """The exact text the model is grounded on, surfaced to the UI for transparency."""
    system: str
    catalogue_count: int
    catalogue_sample: str


class PlanResponse(BaseModel):
    valid: bool
    checks: list[Check]
    plan: WeeklyPlan
    summary: WeeklySummary | None = None
    prompt: PromptView


@dataclass
class _Catalogue:
    """The rendered catalogue for one allergen-filter — reused by the LLM call and the prompt panel."""
    products: list[Product]
    text: str
    count: int
    sample: str


_CATALOGUE_CACHE: dict[frozenset[str], _Catalogue] = {}


def _catalogue(store: ProductStore, exclude: frozenset[str]) -> _Catalogue:
    """Build (and cache) the catalogue for an allergen-filter, so it's rendered once per filter, not per request."""
    if exclude not in _CATALOGUE_CACHE:
        products = store.candidates(exclude)
        text = format_catalogue(products)
        sample = "\n".join(text.split("\n")[:1 + SAMPLE_ROWS])   # header + N rows
        _CATALOGUE_CACHE[exclude] = _Catalogue(products, text, len(products), sample)
    return _CATALOGUE_CACHE[exclude]


def _prompt_view(cat: _Catalogue) -> PromptView:
    return PromptView(system=SYSTEM, catalogue_count=cat.count, catalogue_sample=cat.sample)


def _norm_exclude(exclude: list[str]) -> frozenset[str]:
    return frozenset(a for a in exclude if a in ALLERGENS)


def _planner():
    """Lazily import the selected provider — only the chosen client is constructed."""
    if PROVIDER == "gemini":
        from llm.gemini_planner import plan_week
    else:
        from llm.anthropic_planner import plan_week
    return plan_week


def _make_plan(store: ProductStore, exclude: frozenset[str]) -> WeeklyPlan:
    """Build a plan, failing informatively when the filters leave a track empty."""
    cat = _catalogue(store, exclude)
    candidates = cat.products
    if not any(p.dietary_class == "meat" for p in candidates):
        raise RuntimeError("No meat-track products available for the selected filters.")
    if sum(p.dietary_class in ("vegan", "vegetarian") for p in candidates) < 2:
        raise RuntimeError("Not enough vegetarian products available for the selected filters.")
    if USE_FAKE_LLM:
        return fake_plan_week(candidates)
    return _planner()(cat.text)


def _err_detail(e: Exception) -> str:
    if isinstance(e, anthropic.APIError):
        body = getattr(e, "body", None)
        if isinstance(body, dict) and isinstance(body.get("error"), dict):
            msg = body["error"].get("message")
            if msg:
                return f"LLM error: {msg}"
        return f"LLM error: {getattr(e, 'message', str(e))}"
    if isinstance(e, ValidationError):
        return "LLM returned a malformed plan"
    msg = getattr(e, "message", None)       # e.g. google-genai APIError
    if msg:
        return f"LLM error: {msg}"
    return str(e)


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
    try:
        weekly = _make_plan(store, exclude_set)
    except Exception as e:
        log.error("plan failed: %s", e)
        raise HTTPException(status_code=502, detail=_err_detail(e))

    checks = validate_plan(weekly, store, exclude_set)
    valid = all(c.passed for c in checks)
    if not valid:
        # Join failing details into a single error message
        fails = [d for c in checks if not c.passed for d in c.details]
        raise HTTPException(status_code=502, detail=f"Validation failed: {'; '.join(fails[:3])}...")
        
    summary = summarize_plan(weekly, store)
    log.info("plan generated and validated")
    return PlanResponse(valid=True, checks=checks, plan=weekly, summary=summary,
                        prompt=_prompt_view(_catalogue(store, exclude_set)))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/plan/stream")
async def plan_stream(exclude: list[str] = Query(default=[])):
    store = app.state.store
    exclude_set = _norm_exclude(exclude)
    loop = asyncio.get_event_loop()

    async def gen():
        started = time.monotonic()
        fut = loop.run_in_executor(None, _make_plan, store, exclude_set)

        while not fut.done():
            yield _sse("progress", {"elapsed": round(time.monotonic() - started, 1)})
            await asyncio.sleep(1)

        try:
            weekly = fut.result()
        except Exception as e:
            log.error("stream plan failed: %s", e)
            yield _sse("failed", {"detail": _err_detail(e)})
            return

        checks = validate_plan(weekly, store, exclude_set)
        valid = all(c.passed for c in checks)
        
        if not valid:
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
            "prompt": _prompt_view(_catalogue(store, exclude_set)).model_dump(),
        })

    return StreamingResponse(gen(), media_type="text/event-stream")
