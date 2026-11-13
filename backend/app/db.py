import json
import sqlite3
from datetime import datetime, timezone

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY,
    name TEXT, campus TEXT, pathway_id TEXT, credits INTEGER, work_hours INTEGER,
    holds TEXT, interests TEXT, topics TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    url TEXT, kind TEXT, campus TEXT, every_hours REAL, max_depth INTEGER, enabled INTEGER,
    content_hash TEXT, last_run_at TEXT, last_changed_at TEXT, last_status TEXT, last_error TEXT
);
CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES sources(id),
    name TEXT, type TEXT, campus TEXT, audience TEXT, topics TEXT, summary TEXT,
    eligibility TEXT, how_to_start TEXT,
    contact_office TEXT, contact_email TEXT, contact_phone TEXT,
    location_building TEXT, location_room TEXT, hours TEXT, deadline TEXT,
    event_start TEXT, event_end TEXT,
    evidence TEXT, source_url TEXT, fetched_at TEXT, content_hash TEXT,
    origin TEXT, status TEXT, first_seen_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS resources_fts USING fts5(
    name, summary, topics, eligibility, how_to_start,
    content='resources', content_rowid='rowid'
);
-- Triggers keep the FTS index in sync, so ingestion only writes to resources
CREATE TRIGGER IF NOT EXISTS resources_ai AFTER INSERT ON resources BEGIN
    INSERT INTO resources_fts(rowid, name, summary, topics, eligibility, how_to_start)
    VALUES (new.rowid, new.name, new.summary, new.topics, new.eligibility, new.how_to_start);
END;
CREATE TRIGGER IF NOT EXISTS resources_ad AFTER DELETE ON resources BEGIN
    INSERT INTO resources_fts(resources_fts, rowid, name, summary, topics, eligibility, how_to_start)
    VALUES ('delete', old.rowid, old.name, old.summary, old.topics, old.eligibility, old.how_to_start);
END;
CREATE TRIGGER IF NOT EXISTS resources_au AFTER UPDATE ON resources BEGIN
    INSERT INTO resources_fts(resources_fts, rowid, name, summary, topics, eligibility, how_to_start)
    VALUES ('delete', old.rowid, old.name, old.summary, old.topics, old.eligibility, old.how_to_start);
    INSERT INTO resources_fts(rowid, name, summary, topics, eligibility, how_to_start)
    VALUES (new.rowid, new.name, new.summary, new.topics, new.eligibility, new.how_to_start);
END;
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER, resource_id TEXT, message TEXT, created_at TEXT, read INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY,
    source_id TEXT, started_at TEXT, finished_at TEXT,
    rows_new INTEGER DEFAULT 0, rows_changed INTEGER DEFAULT 0, rows_dropped INTEGER DEFAULT 0,
    error TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 0:
            save_profile(json.loads((config.CONFIG_DIR / "demo_profile.json").read_text()), conn)


def _profile_from_row(row: sqlite3.Row) -> dict:
    p = dict(row)
    p["holds"] = json.loads(p["holds"] or "[]")
    p["topics"] = json.loads(p["topics"] or "[]")
    return p


def get_profile(conn: sqlite3.Connection | None = None) -> dict | None:
    conn = conn or connect()
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return _profile_from_row(row) if row else None


def save_profile(p: dict, conn: sqlite3.Connection | None = None) -> dict:
    conn = conn or connect()
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO profile
               (id, name, campus, pathway_id, credits, work_hours, holds, interests, topics, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (p["name"], p["campus"], p["pathway_id"], p["credits"], p["work_hours"],
             json.dumps(p.get("holds", [])), p.get("interests", ""), json.dumps(p.get("topics", [])), now_iso()),
        )
    return get_profile(conn)
