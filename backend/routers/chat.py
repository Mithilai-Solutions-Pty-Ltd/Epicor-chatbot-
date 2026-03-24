"""
============================================================
Chat Router – /api/chat
============================================================
Endpoints:
  POST /api/chat/message   – main Q&A endpoint
  GET  /api/chat/history/{session_id}  – fetch session history
  DELETE /api/chat/history/{session_id} – clear session
============================================================
"""

import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from backend.services.chat_service import get_answer

logger = logging.getLogger("botzi.chat_router")
router = APIRouter()

# ── In-memory session store (simple; upgrade to Redis if scaling) ──
# Format: { session_id: [{"role": ..., "content": ...}, ...] }
_sessions: dict[str, list] = {}
MAX_HISTORY = 20  # max turns to keep per session


# ── Request / Response models ──────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="The user's question")
    session_id: Optional[str] = Field(None,
                          description="Pass existing ID to maintain conversation. "
                                      "Omit to start a new session.")
    environment: str = Field("prod",
                          description="dev / test / prod – affects guidance")
    user_id: str = Field("anonymous",
                          description="Identifier for the user (email or ID)")


class SourceReference(BaseModel):
    file_name: str
    source: str
    page: int           # INTEGER – always a whole number
    doc_type: str
    score: float


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    follow_up_questions: List[str]
    sources: List[SourceReference]
    confidence: str
    cached: bool
    response_time_ms: int
    timestamp: str


# ── POST /api/chat/message ─────────────────────────────────
@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    """
    Main chatbot endpoint.
    - Creates a new session if session_id is not provided
    - Appends to conversation history for follow-up context
    - Returns answer + 3 clickable follow-up questions + top-3 sources
    """
    # Resolve or create session
    session_id = req.session_id or str(uuid.uuid4())
    history = _sessions.get(session_id, [])

    # Guard: empty question
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Call the RAG pipeline
    result = await get_answer(
        question=req.question,
        session_id=session_id,
        conversation_history=history,
        environment=req.environment,
        user_id=req.user_id,
    )

    # Update session history
    history.append({"role": "user",      "content": req.question})
    history.append({"role": "assistant", "content": result["answer"]})
    # Keep only last MAX_HISTORY turns
    _sessions[session_id] = history[-MAX_HISTORY:]

    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        follow_up_questions=result["follow_up_questions"],
        sources=[SourceReference(**s) for s in result["sources"]],
        confidence=result["confidence"],
        cached=result["cached"],
        response_time_ms=result["response_time_ms"],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ── GET /api/chat/history/{session_id} ────────────────────
@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Return the conversation history for a session."""
    history = _sessions.get(session_id, [])
    return {
        "session_id": session_id,
        "turns": len(history) // 2,
        "history": history,
    }


# ── DELETE /api/chat/history/{session_id} ─────────────────
@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear the conversation history for a session (new chat)."""
    _sessions.pop(session_id, None)
    return {"message": f"Session {session_id} cleared.", "session_id": session_id}
