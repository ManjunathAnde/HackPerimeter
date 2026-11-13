"""Groundedness check: every answer sentence must be backed by retrieved rows or the profile."""
import json
import re

from app import config, llm

PROMPT = (config.BACKEND_DIR / "app" / "prompts" / "verify.txt").read_text(encoding="utf-8")
SCHEMA = '{"unsupported": [1]}'
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.split(text or "") if s.strip()]


def verify_grounded(answer: str, rows: list[dict], profile: dict | None = None) -> dict:
    sentences = split_sentences(answer)
    if not sentences:
        return {"grounded": True, "unsupported": [], "checker": "none"}
    facts = [{k: r.get(k) for k in ["name", "summary", "eligibility", "how_to_start", "contact_office",
                                    "contact_email", "contact_phone", "event_start", "evidence"] if r.get(k)} for r in rows]
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(sentences, 1))
    data, provider = llm.complete_json_traced(
        PROMPT.format(resources=json.dumps(facts, indent=1), profile=json.dumps(profile or {}), sentences=numbered), SCHEMA)
    # The model returns sentence numbers, so code (not the model) decides exactly what text is removed
    bad = {int(n) for n in data.get("unsupported", []) if str(n).isdigit() and 1 <= int(n) <= len(sentences)}
    unsupported = [sentences[i - 1] for i in sorted(bad)]
    return {"grounded": not unsupported, "unsupported": unsupported, "checker": provider}


def remove_sentences(answer: str, unsupported: list[str]) -> str:
    return " ".join(s for s in split_sentences(answer) if s not in unsupported)
