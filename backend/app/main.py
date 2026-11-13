import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import config, db, llm
from app.agents import router
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
