"""Router agent: plan -> FTS5 search -> grounded answer. Stale refetch and verification come in Phase 2."""
import json
import re
import time
from datetime import datetime, timezone

from app import config, db, llm
from app.agents import ingestion, verify

PROMPTS = config.BACKEND_DIR / "app" / "prompts"
PLAN_PROMPT = (PROMPTS / "plan.txt").read_text(encoding="utf-8")
ANSWER_PROMPT = (PROMPTS / "answer.txt").read_text(encoding="utf-8")
PLAN_SCHEMA = '{"intent": "string", "searches": [{"query": "string"}], "needs_events": true}'
ANSWER_SCHEMA = '{"answer_text": "string", "matches": [{"resource_id": "string", "why": "string", "first_step": "string"}], "first_step": "string"}'

# Clarkston students first, downtown-only resources last
CAMPUS_RANK = {"clarkston": 0, "perimeter_all": 1, "online": 1, "gsu_wide": 2, "atlanta_only": 3}
MAX_RETRIEVED = 13  # = MAX_SEARCH_HITS + MAX_EVENTS; a lower cut after campus sort dropped gsu_wide rows like LaunchGSU
MAX_SEARCH_HITS = 10  # relevance cut before campus ranking, so weak Clarkston hits can't crowd out strong ones
MAX_EVENTS = 3
STALE_CHECK_TOP = 5
MAX_REFETCH_SOURCES = 1  # one live refetch per chat keeps answers under ~10s
HEALTHY = {"ok", "unchanged"}  # last run succeeded; "unchanged" just means nothing new on the page
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


def search(conn, query: str) -> list[dict]:
    # No type filter: extraction labels the same kind of thing differently (LaunchGSU came out as "service")
    fts = _fts_query(query)
    if not fts:
        return []
    sql = """SELECT r.*, bm25(resources_fts) AS rank FROM resources_fts
             JOIN resources r ON r.rowid = resources_fts.rowid
             WHERE resources_fts MATCH ? ORDER BY rank LIMIT 20"""
    return [dict(row) for row in conn.execute(sql, (fts,))]


def upcoming_events(conn, topics: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = conn.execute("SELECT *, 0.0 AS rank FROM resources WHERE type='event' AND event_start >= ? ORDER BY event_start", (now,))
    return [dict(r) for r in rows if not topics or set(json.loads(r["topics"] or "[]")) & set(topics)]


def retrieve(conn, plan: dict, profile: dict, trace: list) -> list[dict]:
    best: dict[str, dict] = {}
    # A profile-anchored search runs every time, so results don't hinge on how the planner words its queries
    anchor = {"query": " ".join(profile.get("topics", [])) + " " + (profile.get("interests") or "")}
    for s in plan.get("searches", [])[:4] + [anchor]:
        t0 = time.monotonic()
        hits = search(conn, s.get("query", ""))
        trace.append({"step": "search", "detail": f"{s.get('query')!r} -> {len(hits)} rows",
                      "ms": int((time.monotonic() - t0) * 1000)})
        for h in hits:
            if h["id"] not in best or h["rank"] < best[h["id"]]["rank"]:
                best[h["id"]] = h
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    hits = [r for r in best.values() if not (r["type"] == "event" and r["event_start"] and r["event_start"] < now)]
    rows = sorted(hits, key=lambda r: r["rank"])[:MAX_SEARCH_HITS]
    if plan.get("needs_events"):
        events = upcoming_events(conn, profile.get("topics", []))
        trace.append({"step": "search", "detail": f"upcoming events matching profile topics -> {len(events)} rows, using {MAX_EVENTS}", "ms": 0})
        ids = {r["id"] for r in rows}
        rows += [e for e in events if e["id"] not in ids][:MAX_EVENTS]
    rows.sort(key=lambda r: (CAMPUS_RANK.get(r["campus"], 2), r["rank"]))
    # Several department pages and feeds list the same event; keep one row per (name, start time)
    seen, unique = set(), []
    for r in rows:
        key = (r["name"].lower(), r["event_start"] or "")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return [resource_dict(r) for r in unique[:MAX_RETRIEVED]]


def refresh_stale(conn, rows: list[dict], trace: list) -> list[dict]:
    """Refetch sources behind the top rows when their copy is older than STALE_HOURS."""
    now = datetime.now(timezone.utc)
    stale = []
    for r in rows[:STALE_CHECK_TOP]:
        age_h = (now - datetime.fromisoformat(r["fetched_at"])).total_seconds() / 3600
        if age_h >= config.STALE_HOURS and r["source_id"] not in stale:
            stale.append(r["source_id"])
    if not stale:
        trace.append({"step": "freshness", "detail": f"top rows fetched within {config.STALE_HOURS:g}h, no refetch", "ms": 0})
        return rows
    sources = {s["id"]: dict(s) for s in conn.execute(
        f"SELECT id, kind, last_status FROM sources WHERE id IN ({','.join('?' * len(stale))})", stale)}
    refreshed = 0
    for sid in stale:
        copy_date = min(r["fetched_at"] for r in rows if r["source_id"] == sid)[:10]
        src = sources.get(sid, {})
        # The events feed costs ~10 LLM calls to re-extract; it refreshes through "Run now" instead
        if src.get("last_status") not in HEALTHY or src.get("kind") == "localist_api" or refreshed >= MAX_REFETCH_SOURCES:
            trace.append({"step": "freshness", "detail": f"{sid}: using copy from {copy_date}", "ms": 0})
            continue
        t0 = time.monotonic()
        run = ingestion.refresh_source(sid)
        ms = int((time.monotonic() - t0) * 1000)
        refreshed += 1
        if run["error"]:
            trace.append({"step": "refetch", "detail": f"{sid}: live fetch failed, using copy from {copy_date}", "ms": ms})
        else:
            trace.append({"step": "refetch", "detail": f"refetched {sid}: new={run['rows_new']} changed={run['rows_changed']} unchanged={run['rows_unchanged']}", "ms": ms})
    # Reload so cards show the refreshed fields and fetched_at; rows that vanished keep their stored copy
    ids = [r["id"] for r in rows]
    fresh = {row["id"]: resource_dict(row) for row in conn.execute(
        f"SELECT * FROM resources WHERE id IN ({','.join('?' * len(ids))})", ids)}
    return [fresh.get(r["id"], r) for r in rows]


def _history_text(history: list[dict]) -> str:
    return "\n".join(f"{h['role']}: {h['content']}" for h in history[-4:]) or "(none)"


def _resources_text(rows: list[dict]) -> str:
    keep = ["id", "name", "type", "campus", "topics", "summary", "eligibility", "how_to_start", "contact_office",
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
    # Models sometimes return searches as bare strings instead of {"query": ...}
    plan["searches"] = [q if isinstance(q, dict) else {"query": str(q)} for q in plan.get("searches") or []]
    trace.append({"step": "plan", "detail": f"[{provider}] intent={plan.get('intent')!r} searches={[s.get('query') for s in plan.get('searches', [])]} needs_events={plan.get('needs_events')}",
                  "ms": int((time.monotonic() - t0) * 1000)})

    rows = retrieve(conn, plan, profile, trace)
    rows = refresh_stale(conn, rows, trace)
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

    t0 = time.monotonic()
    answer = ans.get("answer_text", "")
    try:
        check = verify.verify_grounded(answer, rows, profile)
        answer = verify.remove_sentences(answer, check["unsupported"])
        result = "grounded" if check["grounded"] else f"removed {len(check['unsupported'])} unsupported sentence(s)"
    except llm.LLMError:
        # Cards are already limited to retrieved rows; an unchecked answer beats no answer on stage
        check = {"grounded": False, "unsupported": [], "checker": "unavailable"}
        result = "verifier unavailable, answer not checked"
    trace.append({"step": "verify", "detail": f"[{check['checker']}] {result}",
                  "ms": int((time.monotonic() - t0) * 1000)})

    return {
        "answer": answer,
        "first_step": ans.get("first_step", ""),
        "matches": matches,
        "trace": trace,
        "verification": {"checker": check["checker"], "removed_sentences": check["unsupported"]},
    }
