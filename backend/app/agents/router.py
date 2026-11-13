"""Router agent: plan -> FTS5 search -> grounded answer. Stale refetch and verification come in Phase 2."""
import json
import re
import time
from datetime import datetime, timezone

from app import config, db, llm

PROMPTS = config.BACKEND_DIR / "app" / "prompts"
PLAN_PROMPT = (PROMPTS / "plan.txt").read_text(encoding="utf-8")
ANSWER_PROMPT = (PROMPTS / "answer.txt").read_text(encoding="utf-8")
PLAN_SCHEMA = '{"intent": "string", "searches": [{"query": "string", "type": "string|null"}], "needs_events": true}'
ANSWER_SCHEMA = '{"answer_text": "string", "matches": [{"resource_id": "string", "why": "string", "first_step": "string"}], "first_step": "string"}'

# Clarkston students first, downtown-only resources last
CAMPUS_RANK = {"clarkston": 0, "perimeter_all": 1, "online": 1, "gsu_wide": 2, "atlanta_only": 3}
MAX_RETRIEVED = 8
MAX_MATCHES = 3
STOPWORDS = {"the", "and", "for", "with", "how", "what", "where", "who", "can", "you", "your", "are", "about", "into"}


def resource_dict(row) -> dict:
    r = dict(row)
    r["topics"] = json.loads(r.get("topics") or "[]")
    r.pop("rank", None)
    return r


def _fts_query(text: str) -> str | None:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOPWORDS]
    return " OR ".join(f'"{w}"*' for w in words) or None


def search(conn, query: str, rtype: str | None = None) -> list[dict]:
    fts = _fts_query(query)
    if not fts:
        return []
    sql = """SELECT r.*, bm25(resources_fts) AS rank FROM resources_fts
             JOIN resources r ON r.rowid = resources_fts.rowid
             WHERE resources_fts MATCH ?"""
    params: list = [fts]
    if rtype:
        sql += " AND r.type = ?"
        params.append(rtype)
    return [dict(row) for row in conn.execute(sql + " ORDER BY rank LIMIT 20", params)]


def upcoming_events(conn, topics: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = conn.execute("SELECT *, 0.0 AS rank FROM resources WHERE type='event' AND event_start >= ? ORDER BY event_start", (now,))
    return [dict(r) for r in rows if not topics or set(json.loads(r["topics"] or "[]")) & set(topics)]


def retrieve(conn, plan: dict, profile: dict, trace: list) -> list[dict]:
    best: dict[str, dict] = {}
    for s in plan.get("searches", [])[:4]:
        t0 = time.monotonic()
        hits = search(conn, s.get("query", ""), s.get("type"))
        trace.append({"step": "search", "detail": f"{s.get('query')!r} type={s.get('type')} -> {len(hits)} rows",
                      "ms": int((time.monotonic() - t0) * 1000)})
        for h in hits:
            if h["id"] not in best or h["rank"] < best[h["id"]]["rank"]:
                best[h["id"]] = h
    if plan.get("needs_events"):
        events = upcoming_events(conn, profile.get("topics", []))
        trace.append({"step": "search", "detail": f"upcoming events matching profile topics -> {len(events)} rows", "ms": 0})
        for e in events:
            best.setdefault(e["id"], e)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [r for r in best.values() if not (r["type"] == "event" and r["event_start"] and r["event_start"] < now)]
    rows.sort(key=lambda r: (CAMPUS_RANK.get(r["campus"], 2), r["rank"]))
    # Calendar feeds can carry the same event; keep one row per event page
    seen, unique = set(), []
    for r in rows:
        key = (r["source_url"], r["name"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return [resource_dict(r) for r in unique[:MAX_RETRIEVED]]


def _history_text(history: list[dict]) -> str:
    return "\n".join(f"{h['role']}: {h['content']}" for h in history[-4:]) or "(none)"


def _resources_text(rows: list[dict]) -> str:
    keep = ["id", "name", "type", "campus", "summary", "eligibility", "how_to_start", "contact_office",
            "contact_email", "contact_phone", "location_building", "location_room", "hours", "deadline",
            "event_start", "source_url"]
    return json.dumps([{("resource_id" if k == "id" else k): r[k] for k in keep if r.get(k)} for r in rows], indent=1)


def handle(message: str, history: list[dict], profile: dict) -> dict:
    conn = db.connect()
    trace = []
    profile_text = json.dumps({k: profile[k] for k in ["name", "campus", "pathway_id", "credits", "work_hours", "holds", "interests", "topics"]})

    t0 = time.monotonic()
    plan, provider = llm.complete_json_traced(
        PLAN_PROMPT.format(profile=profile_text, history=_history_text(history), message=message), PLAN_SCHEMA)
    trace.append({"step": "plan", "detail": f"[{provider}] intent={plan.get('intent')!r} searches={[s.get('query') for s in plan.get('searches', [])]} needs_events={plan.get('needs_events')}",
                  "ms": int((time.monotonic() - t0) * 1000)})

    rows = retrieve(conn, plan, profile, trace)
    by_id = {r["id"]: r for r in rows}

    t0 = time.monotonic()
    ans, provider = llm.complete_json_traced(
        ANSWER_PROMPT.format(profile=profile_text, history=_history_text(history), message=message,
                             resources=_resources_text(rows)), ANSWER_SCHEMA)
    proposed = ans.get("matches", [])
    # Only resources we actually retrieved may become cards
    matches = [{"resource": by_id[m["resource_id"]], "why": m.get("why", ""), "first_step": m.get("first_step", "")}
               for m in proposed if m.get("resource_id") in by_id][:MAX_MATCHES]
    trace.append({"step": "answer", "detail": f"[{provider}] {len(proposed)} matches proposed, {len(matches)} kept",
                  "ms": int((time.monotonic() - t0) * 1000)})

    return {
        "answer": ans.get("answer_text", ""),
        "first_step": ans.get("first_step", ""),
        "matches": matches,
        "trace": trace,
        "verification": {"checker": None, "removed_sentences": []},
    }
