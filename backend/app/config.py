import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
CONFIG_DIR = BACKEND_DIR / "config"

# .env lives at the repo root so backend and frontend share one file
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
DATABASE_PATH = ROOT_DIR / os.getenv("DATABASE_PATH", "backend/data/pathfinder.db")
STALE_HOURS = float(os.getenv("STALE_HOURS", "168"))
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "0") == "1"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "PathfinderBot/0.1")
DEMO_FALLBACK = os.getenv("DEMO_FALLBACK", "0") == "1"
