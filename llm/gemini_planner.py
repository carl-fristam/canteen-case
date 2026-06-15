"""Gemini adapter: plan_week with optional streaming of the model's thinking."""
import time
from typing import Callable

from google import genai
from google.genai import errors, types

from config import GEMINI_MODEL
from schemas import WeeklyPlan
from llm.prompt import SYSTEM

client = genai.Client()   # reads GEMINI_API_KEY / GOOGLE_API_KEY from env

_TRANSIENT = {429, 500, 502, 503, 504}   # overloaded / rate-limited → worth retrying


def _retry(fn, attempts: int = 4):
    """Run fn(), retrying transient Gemini errors with exponential backoff."""
    for i in range(attempts):
        try:
            return fn()
        except errors.APIError as e:
            if getattr(e, "code", None) not in _TRANSIENT or i == attempts - 1:
                raise
            time.sleep(2 ** i)   # 1s, 2s, 4s


def _contents(catalogue_text: str) -> str:
    return ("Catalogue (available products):\n" + catalogue_text
            + "\n\nPlan the full week (5 days x 2 tracks).")


def _config() -> dict:
    return {
        "system_instruction": SYSTEM,
        "response_mime_type": "application/json",
        "response_schema": WeeklyPlan,                 # Gemini validates against the Pydantic schema
        "thinking_config": types.ThinkingConfig(include_thoughts=True),
    }


def plan_week(catalogue_text: str,
              on_thought: Callable[[str], None] | None = None) -> WeeklyPlan:
    # Non-streaming path (e.g. the plain POST /plan endpoint).
    if on_thought is None:
        response = _retry(lambda: client.models.generate_content(
            model=GEMINI_MODEL, contents=_contents(catalogue_text), config=_config()))
        plan = response.parsed
        if not isinstance(plan, WeeklyPlan):
            raise RuntimeError("No plan produced (Gemini returned no parseable output)")
        return plan

    # Streaming path: surface thought summaries, accumulate the JSON answer.
    # A transient failure normally hits before the first chunk, so a retry restarts cleanly.
    def stream_once() -> str:
        json_chunks: list[str] = []
        for chunk in client.models.generate_content_stream(
                model=GEMINI_MODEL, contents=_contents(catalogue_text), config=_config()):
            for cand in (chunk.candidates or []):
                content = cand.content
                for part in (content.parts or []) if content else []:
                    if not getattr(part, "text", None):
                        continue
                    if getattr(part, "thought", False):
                        on_thought(part.text)
                    else:
                        json_chunks.append(part.text)
        return "".join(json_chunks).strip()

    raw = _retry(stream_once)
    if not raw:
        raise RuntimeError("No plan produced (Gemini returned no output)")
    return WeeklyPlan.model_validate_json(raw)
