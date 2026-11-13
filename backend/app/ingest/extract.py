"""LLM extraction plus the evidence-quote check that keeps every stored row traceable to page text."""
import re

from app import config, llm

PROMPT = (config.BACKEND_DIR / "app" / "prompts" / "extract.txt").read_text(encoding="utf-8")
SCHEMA_HINT = """{"resources": [{"name": "string", "type": "string", "campus": "string", "audience": "string",
"topics": ["string"], "summary": "string", "eligibility": "string|null", "how_to_start": "string|null",
"contact_office": "string|null", "contact_email": "string|null", "contact_phone": "string|null",
"location_building": "string|null", "location_room": "string|null", "hours": "string|null",
"deadline": "string|null", "evidence": "string"}]}"""
MAX_PAGE_CHARS = 15000

TYPES = {"office", "center", "program", "org", "opportunity", "event", "service"}
AUDIENCES = {"perimeter", "atlanta", "all_gsu"}
# Which campuses each source default may be narrowed to (never widened)
NARROWER = {
    "gsu_wide": {"gsu_wide", "perimeter_all", "clarkston", "online", "atlanta_only"},
    "perimeter_all": {"perimeter_all", "clarkston", "online"},
    "clarkston": {"clarkston"},
    "online": {"online"},
    "atlanta_only": {"atlanta_only"},
}
QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u200b": "", "\ufeff": ""})


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").translate(QUOTES)).strip().lower()


def evidence_ok(evidence: str, page_text: str) -> bool:
    ev = normalize(evidence)
    return len(ev) >= 10 and ev in normalize(page_text)


# max_rows=5 keeps the JSON under Groq's 900-token output cap (8 rows came back cut off)
def extract(page_text: str, source: dict, max_rows: int = 5) -> tuple[list[dict], int, str]:
    """Returns (valid rows, dropped count, llm provider)."""
    page_text = page_text[:MAX_PAGE_CHARS]
    prompt = PROMPT.format(source_id=source["id"], url=source["url"], campus=source["campus"],
                           max_rows=max_rows, page_text=page_text)
    data, provider = llm.complete_json_traced(prompt, SCHEMA_HINT)
    rows, dropped = [], 0
    for r in data.get("resources", []):
        if not r.get("name") or not evidence_ok(r.get("evidence", ""), page_text):
            dropped += 1
            continue
        if r.get("campus") not in NARROWER[source["campus"]]:
            r["campus"] = source["campus"]
        if r.get("type") not in TYPES:
            r["type"] = "service"
        if r.get("audience") not in AUDIENCES:
            r["audience"] = "perimeter" if source["campus"] == "perimeter_all" else "all_gsu"
        r["topics"] = [str(t).lower() for t in (r.get("topics") or [])][:5]
        rows.append(r)
    return rows, dropped, provider
