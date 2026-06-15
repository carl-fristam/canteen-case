import os

from dotenv import load_dotenv

load_dotenv()   # read GEMINI_API_KEY from .env

DB_PATH = "data/products.duckdb"
GEMINI_MODEL = "gemini-2.5-flash"