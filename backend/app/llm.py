"""Single entry point for every LLM call: Gemini first, Groq on error or bad JSON."""
import json
import logging
import re

from google import genai
from google.genai import types
from groq import Groq

from app import config

log = logging.getLogger("pathfinder.llm")

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")
LIST_KEY_RE = re.compile(r'^\s*\{\s*"(\w+)"\s*:\s*\[')
GROQ_MAX_TOKENS = 900  # Groq free tier rejects requests whose max output exceeds 1000 tokens/min


class LLMError(Exception):
    pass


def _parse(text: str, schema_hint: str = "") -> dict:
    # Qwen3-family models can emit reasoning before the JSON; drop it before parsing
    text = THINK_RE.sub("", text or "").strip()
    text = FENCE_RE.sub("", text).strip()
    data = json.loads(text)
    # Gemini sometimes returns the bare list when the schema is {"key": [...]}; restore the wrapper
    m = LIST_KEY_RE.match(schema_hint)
    if isinstance(data, list) and m:
        data = {m.group(1): data}
    if not isinstance(data, dict):
        raise ValueError("LLM JSON is not an object")
    return data


def _call_gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
    )
    return resp.text


def _call_groq(prompt: str) -> str:
    if not config.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY not set")
    client = Groq(api_key=config.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=GROQ_MAX_TOKENS,
    )
    return resp.choices[0].message.content


PROVIDERS = [("gemini", _call_gemini), ("groq", _call_groq)]


def complete_json_traced(prompt: str, schema_hint: str) -> tuple[dict, str]:
    """Returns (parsed JSON, provider name). Raises LLMError if every provider fails."""
    full_prompt = f"{prompt}\n\nRespond with ONLY a JSON object matching this shape:\n{schema_hint}"
    errors = []
    for name, call in PROVIDERS:
        # One retry on the same provider for invalid JSON; API errors fail over immediately
        for attempt in range(2):
            try:
                text = call(full_prompt)
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
                break
            try:
                return _parse(text, schema_hint), name
            except ValueError as e:  # json.JSONDecodeError is a ValueError
                errors.append(f"{name} attempt {attempt + 1}: invalid JSON ({e})")
        log.warning("LLM provider %s failed, trying next", name)
    raise LLMError("; ".join(errors))


def complete_json(prompt: str, schema_hint: str) -> dict:
    return complete_json_traced(prompt, schema_hint)[0]
