"""Anthropic adapter: plan_week with optional streaming of the model's thinking."""
from typing import Callable

import anthropic
from anthropic.types import MessageParam, TextBlockParam, RawContentBlockDeltaEvent, ThinkingDelta

from config import MODEL, MAX_TOKENS, EFFORT, THINKING_BUDGET
from schemas import WeeklyPlan
from llm.prompt import SYSTEM

client = anthropic.Anthropic()

_USER: list[MessageParam] = [{"role": "user", "content": "Plan the full week (5 days x 2 tracks)."}]


def _system(catalogue_text: str) -> list[TextBlockParam]:
    # Cache the (large) catalogue block so repeat calls reuse it.
    return [
        {"type": "text", "text": SYSTEM},
        {"type": "text",
         "text": "Catalogue (available products):\n" + catalogue_text,
         "cache_control": {"type": "ephemeral"}},
    ]


def plan_week(catalogue_text: str,
              on_thought: Callable[[str], None] | None = None) -> WeeklyPlan:
    # Non-streaming path (the plain POST /plan endpoint): keep structured-output effort.
    if on_thought is None:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=_system(catalogue_text),
            messages=_USER,
            output_format=WeeklyPlan,
            output_config={"effort": EFFORT} if EFFORT else {},
        )
        if response.parsed_output is None:
            raise RuntimeError(f"No plan produced (stop_reason={response.stop_reason})")
        return response.parsed_output

    # Streaming path: extended thinking gives reasoning deltas to surface live.
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_system(catalogue_text),
        messages=_USER,
        output_format=WeeklyPlan,
        thinking={"type": "enabled", "budget_tokens": THINKING_BUDGET},
    ) as stream:
        for event in stream:
            if isinstance(event, RawContentBlockDeltaEvent) and isinstance(event.delta, ThinkingDelta):
                on_thought(event.delta.thinking)
        raw = stream.get_final_text()

    if not raw.strip():
        raise RuntimeError("No plan produced (Anthropic returned no output)")
    return WeeklyPlan.model_validate_json(raw)
