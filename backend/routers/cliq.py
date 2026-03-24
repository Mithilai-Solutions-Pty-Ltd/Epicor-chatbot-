"""
============================================================
Zoho Cliq Integration Router – /api/cliq
============================================================
This endpoint receives incoming messages from the Zoho Cliq
Bot webhook and returns formatted replies.

SETUP in Zoho Cliq (India DC):
  1. Go to https://cliq.zoho.in → Bots → Create Bot
  2. Name: BOTZI
  3. Webhook URL: https://botzi-api.onrender.com/api/cliq/message
  4. Enable: Incoming messages

Cliq sends a POST to your webhook whenever a user messages
the bot. You reply with Cliq message format (JSON).

Zoho Cliq message format docs:
  https://www.zoho.com/cliq/help/restapi/message-format.html
============================================================
"""

import os
import logging
from fastapi import APIRouter, Request, HTTPException
from backend.services.chat_service import get_answer

logger = logging.getLogger("botzi.cliq")
router = APIRouter()

# In-memory session store for Cliq users
_cliq_sessions: dict[str, dict] = {}


def _format_cliq_response(data: dict, user_name: str) -> dict:
    """
    Convert our chat response into Zoho Cliq message format.
    Supports: text, slides (rich cards), action buttons.
    """
    answer  = data.get("answer", "")
    sources = data.get("sources", [])
    follow_ups = data.get("follow_up_questions", [])
    confidence = data.get("confidence", "medium")
    resp_ms    = data.get("response_time_ms", 0)
    cached     = data.get("cached", False)

    # ── Build text body ────────────────────────────────────
    body_parts = [answer]

    if sources:
        body_parts.append("\n📚 *Sources:*")
        for s in sources:
            body_parts.append(f"  • {s['file_name']} – Page {s['page']}")

    conf_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "🟡")
    cache_tag  = " ⚡ (cached)" if cached else ""
    body_parts.append(f"\n{conf_emoji} Confidence: {confidence} | ⏱️ {resp_ms}ms{cache_tag}")

    # ── Build action buttons for follow-up questions ───────
    buttons = []
    for i, q in enumerate(follow_ups[:3]):
        buttons.append({
            "label": q[:50],   # Cliq button label max ~50 chars
            "type":  "invoke",
            "action": {
                "type": "invoke.function",
                "name": "botzi_followup",
                "data": {"question": q},
            },
        })

    # ── Cliq message payload ───────────────────────────────
    payload = {
        "text": "\n".join(body_parts),
    }

    if buttons:
        payload["slides"] = [{
            "type":    "text",
            "title":   "💡 You might also ask:",
            "buttons": buttons,
        }]

    return payload


@router.post("/cliq/message")
async def cliq_webhook(request: Request):
    """
    Receive Zoho Cliq bot messages and reply with BOTZI answers.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"Cliq webhook payload: {body}")

    # Extract fields from Cliq payload
    # Cliq sends: { "name": "...", "bot": {...}, "text": "...", "user": {...} }
    text      = body.get("text", "").strip()
    user_info = body.get("user", {})
    user_name = user_info.get("name", "anonymous")
    user_id   = user_info.get("id", user_name)

    if not text:
        return {"text": "Hi! I'm BOTZI – your Epicor support assistant. Ask me anything! 🤖"}

    # Manage session per Cliq user
    session_data = _cliq_sessions.get(user_id, {"session_id": None, "history": []})

    # Call RAG pipeline
    result = await get_answer(
        question=text,
        session_id=session_data.get("session_id") or user_id,
        conversation_history=session_data.get("history", []),
        environment="prod",
        user_id=user_id,
    )

    # Update session
    history = session_data.get("history", [])
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant", "content": result["answer"]})
    _cliq_sessions[user_id] = {
        "session_id": user_id,
        "history":    history[-12:],  # keep last 6 turns
    }

    # Format and return Cliq response
    return _format_cliq_response(result, user_name)


@router.post("/cliq/followup")
async def cliq_followup(request: Request):
    """
    Handle follow-up button clicks from Cliq action buttons.
    Cliq sends the function invocation here.
    """
    body    = await request.json()
    data    = body.get("data", {})
    question = data.get("question", "")
    user_info = body.get("user", {})
    user_id   = user_info.get("id", "anonymous")

    if not question:
        return {"text": "Please type your question."}

    session_data = _cliq_sessions.get(user_id, {"session_id": None, "history": []})
    result = await get_answer(
        question=question,
        session_id=session_data.get("session_id") or user_id,
        conversation_history=session_data.get("history", []),
        environment="prod",
        user_id=user_id,
    )

    history = session_data.get("history", [])
    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": result["answer"]})
    _cliq_sessions[user_id] = {"session_id": user_id, "history": history[-12:]}

    return _format_cliq_response(result, user_info.get("name", "user"))
