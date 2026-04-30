from __future__ import annotations
import sys
print("=== START: importing modules ===", flush=True)
import os
print("=== os imported ===", flush=True)
from fastapi import FastAPI
print("=== fastapi imported ===", flush=True)

try:
    from RAG_pipeline.building_retriever import rag_pipeline
    print("=== RAG pipeline imported OK ===", flush=True)
except Exception as e:
    print(f"=== RAG IMPORT FAILED: {e} ===", flush=True)
    sys.exit(1)

import json
import uuid
import os
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel



# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Vietnam Tourism Chatbot API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # production: đổi thành domain FE cụ thể
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store ───────────────────────────────────────────────────
# Key: session_id  →  Value: { "history": [...], "created_at": ..., "title": ... }
SESSIONS: Dict[str, dict] = {}

SESSIONS_DIR = "chat_sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Schemas
# ══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: Optional[str] = None   # None → tạo session mới
    query: str

class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: str

class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str


# ══════════════════════════════════════════════════════════════════════════════
# Session helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get_or_create_session(session_id: Optional[str]) -> str:
    if session_id and session_id in SESSIONS:
        return session_id

    # Tạo mới
    sid = str(uuid.uuid4())[:8]
    SESSIONS[sid] = {
        "title":      "Phiên chat mới",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history":    [],   # [{"role": "user"|"assistant", "content": "..."}]
    }
    _persist_session(sid)
    return sid


def _persist_session(sid: str):
    path = os.path.join(SESSIONS_DIR, f"{sid}.json")
    data = {"id": sid, **SESSIONS[sid]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_sessions_from_disk():
    """Load tất cả phiên đã lưu khi server khởi động."""
    for fname in os.listdir(SESSIONS_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSIONS_DIR, fname), encoding="utf-8") as f:
                data = json.load(f)
            sid = data.pop("id")
            SESSIONS[sid] = data
        except Exception:
            continue


# Load sessions khi startup
@app.on_event("startup")
async def startup():
    _load_sessions_from_disk()
    print(f"✅ Loaded {len(SESSIONS)} sessions from disk")


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def health():
    return {"status": "ok", "service": "Vietnam Tourism Chatbot"}


# ── Session management ────────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionCreateResponse)
def create_session():
    """Tạo phiên chat mới."""
    sid = _get_or_create_session(None)
    return {"session_id": sid, "created_at": SESSIONS[sid]["created_at"]}


@app.get("/sessions", response_model=List[SessionInfo])
def list_sessions():
    """Lấy danh sách tất cả phiên, sort mới nhất lên đầu."""
    result = []
    for sid, s in SESSIONS.items():
        result.append(SessionInfo(
            session_id=    sid,
            title=         s.get("title", "Phiên chat mới"),
            created_at=    s.get("created_at", ""),
            updated_at=    s.get("updated_at", ""),
            message_count= len(s.get("history", [])),
        ))
    return sorted(result, key=lambda x: x.updated_at, reverse=True)


@app.get("/sessions/{session_id}/messages", response_model=List[Message])
def get_messages(session_id: str):
    """Lấy toàn bộ lịch sử chat của một phiên."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    return SESSIONS[session_id].get("history", [])


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Xóa phiên chat."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    SESSIONS.pop(session_id)
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)
    return {"deleted": session_id}


# ── Chat (streaming SSE) ──────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest):
    """
    Gửi câu hỏi, nhận câu trả lời dạng SSE stream.

    Client đọc từng event:
        data: {"token": "Xin", "done": false}
        data: {"token": " chào", "done": false}
        ...
        data: {"token": "", "done": true, "session_id": "abc12345"}
    """
    sid = _get_or_create_session(req.session_id)
    session = SESSIONS[sid]
    history: List[Dict] = session.get("history", [])

    def event_stream():
        full_answer_parts = []

        try:
            for token in rag_pipeline(query=req.query, chat_history=history):
                full_answer_parts.append(token)
                payload = json.dumps({"token": token, "done": False}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

        except Exception as e:
            err = json.dumps({"error": str(e), "done": True})
            yield f"data: {err}\n\n"
            return

        # Stream xong → cập nhật history + auto-title + persist
        full_answer = "".join(full_answer_parts)

        history.append({"role": "user",      "content": req.query})
        history.append({"role": "assistant", "content": full_answer})
        session["history"]    = history
        session["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Auto-title từ câu hỏi đầu tiên
        if session["title"] == "Phiên chat mới":
            title = req.query.strip()
            session["title"] = title[:45] + "…" if len(title) > 45 else title

        _persist_session(sid)

        # Done event
        done_payload = json.dumps({
            "token":      "",
            "done":       True,
            "session_id": sid,
            "title":      session["title"],
        }, ensure_ascii=False)
        yield f"data: {done_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # tắt nginx buffer nếu có
        },
    )
