import os

from dotenv import load_dotenv

load_dotenv()   # read ANTHROPIC_API_KEY / USE_FAKE_LLM from .env

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 20000
DB_PATH = "data/products.duckdb"
USE_FAKE_LLM = os.getenv("USE_FAKE_LLM") == "1"

# Which provider to call on the real path: anthropic | gemini
PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
GEMINI_MODEL = "gemini-2.5-flash"

# Set to None for models that don't support effort (e.g. Haiku 4.5).
EFFORT = "high"          # low | medium | high | max | None