"""HEYRA API: Menu planning with live reasoning stream."""
import asyncio, json, logging
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from data.product_store import ProductStore
from llm.gemini import plan_week
from llm.prompt import format_catalogue
from services.validate import validate_plan
from services.summarize import summarize_plan

app = FastAPI(title="HEYRA Planner")
store = ProductStore()

@app.get("/", response_class=HTMLResponse)
def index():
    return Path("frontend/index.html").read_text()

@app.get("/plan")
async def generate_plan(exclude: list[str] = Query(default=[])):
    exclude_set = frozenset(a for a in exclude if a in ("gluten", "nuts", "dairy"))
    products = store.candidates(exclude_set)
    catalogue = format_catalogue(products)
    loop, queue = asyncio.get_event_loop(), asyncio.Queue()

    def work():
        try:
            if not any(p.dietary_class == "meat" for p in products):
                raise RuntimeError("No meat products available for these filters.")
            p = plan_week(catalogue, lambda t: (loop.call_soon_threadsafe(queue.put_nowait, ("thinking", t)), None)[1])
            fails = validate_plan(p, store, exclude_set)
            if fails: raise RuntimeError(f"Plan invalid: {fails[0]}")
            loop.call_soon_threadsafe(queue.put_nowait, ("done", p))
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

    async def stream():
        asyncio.create_task(asyncio.to_thread(work))
        while True:
            kind, val = await queue.get()
            if kind == "thinking": yield f"event: thinking\ndata: {json.dumps({'text': val})}\n\n"
            if kind == "error":
                yield f"event: failed\ndata: {json.dumps({'detail': val})}\n\n"
                break
            if kind == "done":
                yield f"event: done\ndata: {json.dumps({'valid': True, 'days': [d.model_dump() for d in val.days], 'summary': summarize_plan(val, store).model_dump()})}\n\n"
                break

    return StreamingResponse(stream(), media_type="text/event-stream")
