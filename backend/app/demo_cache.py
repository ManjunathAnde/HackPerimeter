"""Demo fallback: cached answers for the two scripted demo questions, used only when both LLMs fail."""
import json
import re

from app import config

CACHE_PATH = config.BACKEND_DIR / "data" / "demo_cache.json"
STEP2 = "I want to turn my side hustle into a real business. I'm at Perimeter. Where do I start?"
STEP4 = "What's happening at Clarkston for business students this month?"


def key(message: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", message.lower().replace("\u2019", "'")).strip()


def lookup(message: str) -> dict | None:
    if not CACHE_PATH.exists():
        return None
    cached = json.loads(CACHE_PATH.read_text(encoding="utf-8")).get(key(message))
    if cached is None:
        return None
    cached["trace"] = [{"step": "cache", "detail": "cached response: both LLM providers unavailable", "ms": 0}] + cached["trace"]
    return cached


def save(responses: dict[str, dict]) -> None:
    CACHE_PATH.write_text(json.dumps({key(m): r for m, r in responses.items()}, indent=1), encoding="utf-8")
