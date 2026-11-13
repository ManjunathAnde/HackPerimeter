"""Ingestion agent: the only writer to `resources`. fetch -> parse -> extract -> evidence check -> hash diff -> upsert."""
import hashlib
import json
import re

import yaml

from app import config, db, llm
from app.ingest import extract, parse_html, parse_localist, parse_rss
from app.ingest.fetch import fetch

LOCALIST_MAX_PAGES = 6
EVENTS_PER_LLM_CALL = 4  # bigger batches made both LLMs return cut-off JSON
ROW_FIELDS = ["name", "type", "campus", "audience", "topics", "summary", "eligibility", "how_to_start",
              "contact_office", "contact_email", "contact_phone", "location_building", "location_room",
              "hours", "deadline", "event_start", "event_end", "evidence", "source_url"]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def load_sources() -> list[dict]:
    cfg = yaml.safe_load((config.CONFIG_DIR / "sources.yaml").read_text())
    return [{"every_hours": 24, "max_depth": 0, **s} for s in cfg["sources"]]


def sync_sources(conn) -> None:
    """Mirror sources.yaml into the sources table, keeping run state for existing ids."""
    with conn:
        ids = []
        for s in load_sources():
            ids.append(s["id"])
            conn.execute(
                """INSERT INTO sources (id, url, kind, campus, every_hours, max_depth, enabled)
                   VALUES (?, ?, ?, ?, ?, ?, 1)
                   ON CONFLICT(id) DO UPDATE SET url=excluded.url, kind=excluded.kind, campus=excluded.campus,
                   every_hours=excluded.every_hours, max_depth=excluded.max_depth, enabled=1""",
                (s["id"], s["url"], s["kind"], s["campus"], s["every_hours"], s["max_depth"]),
            )
        conn.execute(f"UPDATE sources SET enabled=0 WHERE id NOT IN ({','.join('?' * len(ids))})", ids)


def _fetch_bodies(source: dict) -> tuple[list[str], str]:
    """Most sources are one URL; the Localist API is paginated."""
    body, final_url = fetch(source["url"])
    bodies = [body]
    if source["kind"] == "localist_api":
        total = min(json.loads(body)["page"]["total"], LOCALIST_MAX_PAGES)
        bodies += [fetch(f"{source['url']}&page={n}")[0] for n in range(2, total + 1)]
    return bodies, final_url


def _extract_events_batched(source: dict, events: list[dict]) -> tuple[list[dict], int, list[str]]:
    """Several events per LLM call; each row is tied back to the event whose text holds its evidence quote."""
    rows, dropped, texts = [], 0, []
    for i in range(0, len(events), EVENTS_PER_LLM_CALL):
        batch = events[i:i + EVENTS_PER_LLM_CALL]
        text = "\n\n".join(f"EVENT: {e['text']}" for e in batch)
        try:
            got, d, _ = extract.extract(text, source, max_rows=len(batch))
        except llm.LLMError:
            # One bad batch shouldn't lose the other events in the feed
            dropped += len(batch)
            continue
        dropped += d
        texts += [e["text"] for e in batch]
        for r in got:
            event = next((e for e in batch if extract.evidence_ok(r["evidence"], e["text"])), None)
            if event is None:  # quote spans two events, so we can't say which one it describes
                dropped += 1
                continue
            r.update(type="event", source_url=event["link"], event_start=event["event_start"],
                     event_end=event["event_end"], location_building=r.get("location_building") or event["location"])
            if event["clarkston"]:
                r["campus"] = "clarkston"
            rows.append(r)
    return rows, dropped, texts


def _extract_rows(source: dict, bodies: list[str], final_url: str) -> tuple[list[dict], int, list[str]]:
    """Returns (rows, dropped, page texts used for evidence)."""
    body = bodies[0]
    if source["kind"] == "localist_api":
        return _extract_events_batched(source, parse_localist.parse_events(bodies, source.get("keywords", [])))
    if source["kind"] == "rss":
        rows, dropped, texts = [], 0, []
        for item in parse_rss.parse_items(body):
            got, d, _ = extract.extract(item["text"], source, max_rows=1)
            dropped += d
            texts.append(item["text"])
            for r in got:
                # Code, not the LLM, owns event identity and timing
                r.update(type="event", source_url=item["link"], event_start=item["event_start"])
                rows.append(r)
        return rows, dropped, texts
    if source["kind"] == "page":
        text = parse_html.clean_text(body)
        rows, dropped, _ = extract.extract(text, source)
        for r in rows:
            r["source_url"] = final_url
        return rows, dropped, [text]
    raise ValueError(f"unsupported source kind: {source['kind']}")


def _upsert(conn, source_id: str, r: dict, now: str) -> str:
    """Returns the row status: new, changed or unchanged."""
    row = {f: r.get(f) for f in ROW_FIELDS}
    row["topics"] = json.dumps(row["topics"] or [])
    row_hash = _sha(json.dumps(row, sort_keys=True))
    rid = f"{source_id}:{_slug(row['name'])}"
    old = conn.execute("SELECT content_hash, first_seen_at FROM resources WHERE id=?", (rid,)).fetchone()
    status = "new" if old is None else ("unchanged" if old["content_hash"] == row_hash else "changed")
    row.update(id=rid, source_id=source_id, fetched_at=now, content_hash=row_hash, origin="agent",
               status=status, first_seen_at=old["first_seen_at"] if old else now)
    cols = list(row)
    conn.execute(
        f"INSERT OR REPLACE INTO resources ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        [row[c] for c in cols],
    )
    return status


def run_source(source_id: str) -> dict:
    conn = db.connect()
    sync_sources(conn)
    # yaml-only settings (like keyword filters) ride along with the stored run state
    yaml_entry = next((s for s in load_sources() if s["id"] == source_id), {})
    source = {**yaml_entry, **dict(conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone())}
    started = db.now_iso()
    with conn:
        run_id = conn.execute("INSERT INTO ingestion_runs (source_id, started_at) VALUES (?, ?)",
                              (source_id, started)).lastrowid
    counts = {"new": 0, "changed": 0, "unchanged": 0}
    dropped, error, page_hash, evidence_ok = 0, None, None, 0
    try:
        bodies, final_url = _fetch_bodies(source)
        # Hash visible text for pages: Localist HTML carries per-request tokens that change every fetch
        page_hash = _sha(parse_html.clean_text(bodies[0]) if source["kind"] == "page" else "".join(bodies))
        now = db.now_iso()
        if page_hash == source.get("content_hash"):
            # Content-hash diff: nothing changed, so skip the LLM and just re-stamp the rows as verified now
            with conn:
                counts["unchanged"] = conn.execute(
                    "UPDATE resources SET fetched_at=?, status='unchanged' WHERE source_id=?", (now, source_id)).rowcount
        else:
            rows, dropped, texts = _extract_rows(source, bodies, final_url)
            # Re-check stored evidence against the exact text the rows came from
            evidence_ok = sum(any(extract.evidence_ok(r["evidence"], t) for t in texts) for r in rows)
            with conn:
                for r in rows:
                    counts[_upsert(conn, source_id, r, now)] += 1
    except Exception as e:  # a failed run must still be logged and must not crash the caller
        error = f"{type(e).__name__}: {e}"
    finished = db.now_iso()
    changed_any = counts["new"] + counts["changed"] > 0
    with conn:
        conn.execute("UPDATE ingestion_runs SET finished_at=?, rows_new=?, rows_changed=?, rows_dropped=?, error=? WHERE id=?",
                     (finished, counts["new"], counts["changed"], dropped, error, run_id))
        conn.execute(
            """UPDATE sources SET last_run_at=?, last_status=?, last_error=?,
               content_hash=COALESCE(?, content_hash),
               last_changed_at=CASE WHEN ? THEN ? ELSE last_changed_at END WHERE id=?""",
            (finished, "error" if error else ("ok" if changed_any else "unchanged"), error,
             page_hash, changed_any, finished, source_id),
        )
    run = dict(conn.execute("SELECT * FROM ingestion_runs WHERE id=?", (run_id,)).fetchone())
    run["rows_unchanged"] = counts["unchanged"]
    run["evidence_verified"] = evidence_ok
    return run


def refresh_source(source_id: str) -> dict:
    """Same pipeline, called by the router when stored rows are stale."""
    return run_source(source_id)
