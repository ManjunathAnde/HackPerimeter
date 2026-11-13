"""Watcher agent: after each ingestion run, alert the student about new or changed rows that fit their profile."""
import json
from datetime import datetime, timezone

from app import db


def _fits(row, topics: set[str], now: str) -> bool:
    row_topics = set(json.loads(row["topics"] or "[]"))
    if not row_topics & topics:
        return False
    if row["campus"] == "atlanta_only" and "transition" not in row_topics:
        return False
    if row["type"] == "event" and not (row["event_start"] and row["event_start"] >= now):
        return False
    return True


def process_run(run_id: int, label: str | None = None) -> int:
    """Returns the number of alerts created. `label` names the source in the message, e.g. "ENI"."""
    conn = db.connect()
    run = conn.execute("SELECT * FROM ingestion_runs WHERE id = ?", (run_id,)).fetchone()
    profile = db.get_profile(conn)
    if run is None or run["error"] or profile is None:
        return 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT * FROM resources WHERE source_id = ? AND status IN ('new', 'changed') AND fetched_at >= ?",
        (run["source_id"], run["started_at"]),
    ).fetchall()
    created = 0
    with conn:
        for row in rows:
            if not _fits(row, set(profile["topics"]), now):
                continue
            # One alert per resource: LLM re-extraction rewords rows, which must not re-alert
            if conn.execute("SELECT 1 FROM alerts WHERE resource_id = ?", (row["id"],)).fetchone():
                continue
            kind = "event" if row["type"] == "event" else "resource"
            prefix = f"New {label} {kind}" if label else f"New {kind}"
            conn.execute(
                "INSERT INTO alerts (profile_id, resource_id, message, created_at, read) VALUES (?, ?, ?, ?, 0)",
                (profile["id"], row["id"], f"{prefix} matches your interests: {row['name']}", db.now_iso()),
            )
            created += 1
    return created
