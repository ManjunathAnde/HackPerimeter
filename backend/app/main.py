from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import config, db, llm
from app.agents import router
from app.models import ChatRequest, Profile

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
