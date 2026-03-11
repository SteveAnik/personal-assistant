import uuid
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from config import settings
from memory import MemoryManager
from agent import Agent
from providers import list_providers
from admin_api import make_router

log = structlog.get_logger()
memory_manager: MemoryManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_manager
    log.info("starting_agent_core")
    memory_manager = MemoryManager(settings.database_url)
    await memory_manager.init()
    app.include_router(make_router(settings.database_url), dependencies=[Depends(verify_key)])
    log.info("database_connected")
    yield
    await memory_manager.close()
    log.info("shutdown_complete")


app = FastAPI(title="Personal Assistant Agent Core", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def verify_key(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.replace("Bearer ", "")
    if token != settings.agent_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


# ── Admin UI ───────────────────────────────────────────────────────────────────
@app.get("/admin")
async def admin_ui():
    path = os.path.join(static_dir, "admin.html")
    return FileResponse(path)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}


# ── OpenAI-compatible /v1/chat/completions ─────────────────────────────────────
class OAIMessage(BaseModel):
    role: str
    content: str


class OAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: list[OAIMessage]
    stream: Optional[bool] = False


@app.post("/v1/chat/completions", dependencies=[Depends(verify_key)])
async def openai_compat_chat(req: OAIChatRequest):
    session_id = f"webui-{uuid.uuid4().hex[:8]}"
    user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    agent = Agent(memory_manager, db_pool=memory_manager.pool)
    result = await agent.run(user_msg, session_id, provider_name=req.model)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "model": req.model or settings.active_provider,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": result}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# ── Native /chat endpoint ──────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider: Optional[str] = None


@app.post("/chat", dependencies=[Depends(verify_key)])
async def chat(req: ChatRequest):
    session_id = req.session_id or f"session-{uuid.uuid4().hex[:8]}"
    agent = Agent(memory_manager, db_pool=memory_manager.pool)
    result = await agent.run(req.message, session_id, provider_name=req.provider)
    return {"response": result, "session_id": session_id}


# ── Memory endpoints ───────────────────────────────────────────────────────────
class MemoryRequest(BaseModel):
    content: str
    category: str = "general"
    importance: float = 0.5


@app.post("/memory", dependencies=[Depends(verify_key)])
async def add_memory(req: MemoryRequest):
    mem_id = await memory_manager.save_memory(req.content, req.category, importance=req.importance)
    return {"id": mem_id, "content": req.content}


@app.get("/memory/search", dependencies=[Depends(verify_key)])
async def search_memory(q: str = "", limit: int = 5, category: Optional[str] = None):
    results = await memory_manager.search_memories(q or "general", limit=limit, category=category)
    return {"results": results}


# ── Provider management ────────────────────────────────────────────────────────
@app.get("/providers", dependencies=[Depends(verify_key)])
async def get_providers():
    return {"providers": list_providers()}


# ── Session management ─────────────────────────────────────────────────────────
@app.get("/sessions", dependencies=[Depends(verify_key)])
async def get_sessions():
    sessions = await memory_manager.list_sessions()
    return {"sessions": sessions}


@app.get("/sessions/{session_id}", dependencies=[Depends(verify_key)])
async def get_session(session_id: str, limit: int = 50):
    history = await memory_manager.get_conversation(session_id, limit=limit)
    return {"session_id": session_id, "messages": history}


# ── OpenAI-compatible /v1/models (required by Open WebUI) ─────────────────────
@app.get("/v1/models", dependencies=[Depends(verify_key)])
async def list_models():
    providers = list_providers()
    models = [
        {"id": p["name"], "object": "model", "owned_by": p["name"], "permission": []}
        for p in providers if p["configured"]
    ]
    return {"object": "list", "data": models}
