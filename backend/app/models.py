from pydantic import BaseModel


class Profile(BaseModel):
    name: str
    campus: str
    pathway_id: str
    credits: int
    work_hours: int
    holds: list[str] = []
    interests: str = ""
    topics: list[str] = []


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
