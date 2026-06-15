import anthropic

from config import MODEL, MAX_TOKENS, EFFORT
from schemas import WeeklyPlan
from llm.prompt import SYSTEM

client = anthropic.Anthropic()


def plan_week(catalogue_text: str) -> WeeklyPlan:
    opts = {}
    if EFFORT:
        opts["output_config"] = {"effort": EFFORT}

    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {"type": "text", "text": SYSTEM},
            {"type": "text",
             "text": "Catalogue (available products):\n" + catalogue_text,
             "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": "Plan the full week (5 days x 2 tracks)."}],
        output_format=WeeklyPlan,
        **opts,
    )
    if response.parsed_output is None:
        raise RuntimeError(f"No plan produced (stop_reason={response.stop_reason})")
    return response.parsed_output