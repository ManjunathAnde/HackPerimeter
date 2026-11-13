import json

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import config, db, demo_cache, llm
from app.agents import ingestion, router
from app.models import ChatRequest, DraftEmailRequest, Profile

app = FastAPI(title="Pathfinder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
db.init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "db": config.DATABASE_PATH.exists(), "llm_primary": "gemini"}


@app.get("/api/profile")
def get_profile():
    return db.get_profile()


@app.put("/api/profile")
def put_profile(profile: Profile):
    return db.save_profile(profile.model_dump())


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        return router.handle(req.message, [m.model_dump() for m in req.history], db.get_profile())
    except llm.LLMError as e:
        cached = demo_cache.lookup(req.message) if config.DEMO_FALLBACK else None
        if cached:
            return cached
        raise HTTPException(status_code=503, detail=f"Both LLM providers failed: {e}")


EMAIL_PROMPT = (config.BACKEND_DIR / "app" / "prompts" / "email.txt").read_text(encoding="utf-8")
EMAIL_FIELDS = ["name", "type", "summary", "eligibility", "how_to_start", "contact_office", "event_start", "source_url"]


@app.post("/api/draft-email")
def draft_email(req: DraftEmailRequest):
    row = db.connect().execute("SELECT * FROM resources WHERE id = ?", (req.resource_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown resource")
    resource = router.resource_dict(row)
    profile = db.get_profile()
    prompt = EMAIL_PROMPT.format(
        profile=json.dumps({k: profile[k] for k in ["name", "campus", "pathway_id", "credits", "work_hours", "interests"]}),
        resource=json.dumps({k: resource[k] for k in EMAIL_FIELDS if resource.get(k)}),
        greeting_target=resource.get("contact_office") or f"{resource['name']} team",
    )
    try:
        data = llm.complete_json(prompt, '{"subject": "string", "body": "string"}')
    except llm.LLMError as e:
        raise HTTPException(status_code=503, detail=f"Both LLM providers failed: {e}")
    # "to" comes only from the stored row, never from the model
    return {"to": resource.get("contact_email"), "subject": data.get("subject", ""),
            "body": data.get("body", ""), "contact_url": resource["source_url"]}



@app.get("/api/alerts")
def list_alerts(unread: int = 0):
    sql = """SELECT a.*, r.name AS resource_name, r.source_url FROM alerts a
             LEFT JOIN resources r ON r.id = a.resource_id"""
    if unread:
        sql += " WHERE a.read = 0"
    return [dict(row) for row in db.connect().execute(sql + " ORDER BY a.id DESC")]


@app.post("/api/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int):
    with db.connect() as conn:
        conn.execute("UPDATE alerts SET read = 1 WHERE id = ?", (alert_id,))
    return {"ok": True}


@app.get("/api/sources")
def list_sources():
    conn = db.connect()
    ingestion.sync_sources(conn)
    # Latest run per source supplies the row counts shown in the table
    rows = conn.execute(
        """SELECT s.*, r.rows_new, r.rows_changed, r.rows_dropped, r.error AS run_error,
                  (SELECT COUNT(*) FROM resources WHERE source_id = s.id) AS rows_total
           FROM sources s
           LEFT JOIN ingestion_runs r ON r.id = (SELECT MAX(id) FROM ingestion_runs WHERE source_id = s.id)
           WHERE s.enabled = 1 ORDER BY s.id"""
    )
    return [dict(row) for row in rows]


@app.post("/api/sources/{source_id}/run")
def run_source(source_id: str):
    if source_id not in {s["id"] for s in ingestion.load_sources()}:
        raise HTTPException(status_code=404, detail="Unknown source")
    run = ingestion.run_source(source_id)
    return {"run": run, "alerts_created": run["alerts_created"]}


@app.post("/api/ingest/run-all")
def run_all():
    runs = [ingestion.run_source(s["id"]) for s in ingestion.load_sources()]
    return {"runs": runs, "alerts_created": sum(r["alerts_created"] for r in runs)}



def load_pathways() -> list[dict]:
    return yaml.safe_load((config.CONFIG_DIR / "pathways.yaml").read_text(encoding="utf-8"))


def _step_resources(conn, step: dict) -> list[dict]:
    fts = router._fts_query(step["query"])
    rows = conn.execute(
        """SELECT r.* FROM resources_fts JOIN resources r ON r.rowid = resources_fts.rowid
           WHERE resources_fts MATCH ? AND r.source_id = ? ORDER BY bm25(resources_fts) LIMIT 1""",
        (fts, step["source_id"]),
    ).fetchall()
    return [router.resource_dict(r) for r in rows]


@app.get("/api/pathways")
def list_pathways():
    return [{k: p[k] for k in ["id", "name", "focus", "start", "destination"]} for p in load_pathways()]


@app.get("/api/pathways/{pathway_id}/roadmap")
def roadmap(pathway_id: str):
    pathway = next((p for p in load_pathways() if p["id"] == pathway_id), None)
    if pathway is None:
        raise HTTPException(status_code=404, detail="Unknown pathway")
    conn = db.connect()
    steps = [{"title": s["title"], "source_id": s["source_id"], "resources": _step_resources(conn, s)} for s in pathway["steps"]]
    # Only steps backed by a real KB row are shown; no template steps
    return {"pathway": {k: v for k, v in pathway.items() if k != "steps"}, "steps": [s for s in steps if s["resources"]]}


@app.get("/api/stats")
def kb_stats():
    by_type = {r["type"]: r["n"] for r in db.connect().execute("SELECT type, COUNT(*) AS n FROM resources GROUP BY type")}
    return {"total": sum(by_type.values()), "by_type": by_type}
