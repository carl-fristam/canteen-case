"""HEYRA Planner: Primary adapter for Gemini thinking models. 
Streams reasoning (thoughts) and returns a validated WeeklyPlan JSON object.
"""
import time
from typing import Callable

from google import genai
from google.genai import errors, types

from config import GEMINI_MODEL
from schemas import WeeklyPlan
from llm.prompt import SYSTEM

client = genai.Client()

_TRANSIENT = {429, 500, 502, 503, 504}


def _retry(fn, attempts: int = 4):
    for i in range(attempts):
        try:
            return fn()
        except errors.APIError as e:
            if getattr(e, "code", None) not in _TRANSIENT or i == attempts - 1:
                raise
            time.sleep(2 ** i)


def _contents(catalogue_text: str) -> str:
    return ("Catalogue (available products):\n" + catalogue_text
            + "\n\nPlan the full week (5 days x 2 tracks).")


def _config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SYSTEM,
        response_mime_type="application/json",
        response_schema=WeeklyPlan,
        thinking_config=types.ThinkingConfig(include_thoughts=True),
    )


def plan_week(catalogue_text: str,
              on_thought: Callable[[str], None]) -> WeeklyPlan:
    def stream_once() -> str:
        json_chunks: list[str] = []
        for chunk in client.models.generate_content_stream(
                model=GEMINI_MODEL, contents=_contents(catalogue_text), config=_config()):
            for cand in (chunk.candidates or []):
                content = cand.content
                for part in (content.parts or []) if content else []:
                    if getattr(part, "thought", False):
                        if text := getattr(part, "text", None):
                            on_thought(text)
                    elif text := getattr(part, "text", None):
                        json_chunks.append(text)
        return "".join(json_chunks).strip()

    raw = _retry(stream_once)
    if not raw:
        raise RuntimeError("No plan produced (Gemini returned no output)")
    return WeeklyPlan.model_validate_json(raw)
