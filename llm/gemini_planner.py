"""Gemini adapter: same signature as generate_plan.plan_week."""
from google import genai

from config import GEMINI_MODEL
from schemas import WeeklyPlan
from llm.prompt import SYSTEM

client = genai.Client()   # reads GEMINI_API_KEY / GOOGLE_API_KEY from env


def plan_week(catalogue_text: str) -> WeeklyPlan:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=(
            "Catalogue (available products):\n" + catalogue_text
            + "\n\nPlan the full week (5 days x 2 tracks)."
        ),
        config={
            "system_instruction": SYSTEM,
            "response_mime_type": "application/json",
            "response_schema": WeeklyPlan,     # Gemini validates against the Pydantic schema
        },
    )
    plan = response.parsed
    if not isinstance(plan, WeeklyPlan):
        raise RuntimeError("No plan produced (Gemini returned no parseable output)")
    return plan
