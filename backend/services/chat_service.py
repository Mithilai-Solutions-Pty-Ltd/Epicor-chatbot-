"""
============================================================
Chat Service – Core RAG Pipeline
============================================================
Flow:
  1. Check cache  → return instantly if hit
  2. Query Pinecone for relevant chunks
  3. Build prompt with strict grounding instructions
  4. Call GPT-4o-mini
  5. Parse response (answer + follow-up questions)
  6. Cache result
  7. Log to Supabase (async)
============================================================
"""

import os
import json
import hashlib
import logging
import time
from typing import List, Dict, Any, Tuple

from openai import OpenAI

from backend.services.pinecone_service import query_index
from backend.services.cache_service import cache
from backend.services.supabase_service import log_interaction

logger = logging.getLogger("botzi.chat")
_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── System prompt (anti-hallucination + grounding) ────────
SYSTEM_PROMPT = """You are BOTZI, the official Epicor ERP technical support assistant for Mithilai Solutions.

CRITICAL RULES – follow these without exception:
1. Answer ONLY from the provided document context below.
2. If the answer is not found in the context, reply:
   "I couldn't find this in the available documentation. Please raise a support ticket or contact your Epicor administrator."
3. Never guess, fabricate, or infer beyond what the context says.
4. Be concise, structured, and professional.
5. Always mention the environment (Dev/Test/Prod) when giving configuration steps if the user specified one.
6. End every response with exactly 3 clickable follow-up questions in JSON format (see OUTPUT FORMAT).

OUTPUT FORMAT – respond with valid JSON only:
{
  "answer": "<your full answer in markdown>",
  "follow_up_questions": [
    "Question 1?",
    "Question 2?",
    "Question 3?"
  ],
  "confidence": "<high|medium|low>"
}

Do not add any text outside the JSON object.
"""


def _make_cache_key(question: str, session_id: str) -> str:
    """SHA-256 hash of question text (session-agnostic for shared cache)."""
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()


def _build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt."""
    if not chunks:
        return "No relevant documentation found."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}] {chunk['file_name']} | Page {chunk['page']} | Score: {chunk['score']}\n"
            f"{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _parse_llm_response(raw: str) -> Dict[str, Any]:
    """Parse the JSON response from GPT. Falls back gracefully."""
    try:
        # Strip markdown fences if present
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(cleaned)
    except Exception:
        logger.warning("LLM response was not valid JSON – wrapping as plain answer")
        return {
            "answer": raw,
            "follow_up_questions": [],
            "confidence": "low",
        }


def _build_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build the top-3 source references list.
    Page numbers are guaranteed to be integers.
    """
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk["file_name"], chunk["page"])
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "file_name": chunk["file_name"],
            "source":    chunk["source"],
            "page":      int(chunk["page"]),   # INTEGER TYPE – critical for trust
            "doc_type":  chunk["doc_type"],
            "score":     chunk["score"],
        })
        if len(sources) == 3:
            break
    return sources


# ── Public API ────────────────────────────────────────────
async def get_answer(
    question: str,
    session_id: str,
    conversation_history: List[Dict[str, str]],
    environment: str = "prod",
    user_id: str = "anonymous",
) -> Dict[str, Any]:
    """
    Main entry point called by the chat router.

    Returns:
    {
      "answer":              str (markdown),
      "follow_up_questions": List[str],
      "sources":             List[{file_name, source, page(int), doc_type, score}],
      "confidence":          str,
      "cached":              bool,
      "response_time_ms":    int,
    }
    """
    start = time.time()
    cache_key = _make_cache_key(question, session_id)
    cache_ttl = int(os.environ.get("CACHE_TTL", "3600"))
    top_k = int(os.environ.get("TOP_K_RESULTS", "5"))

    # ── 1. Cache check ─────────────────────────────────────
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"Cache HIT for key={cache_key[:8]}...")
        cached["cached"] = True
        cached["response_time_ms"] = int((time.time() - start) * 1000)
        return cached

    # ── 2. Retrieve relevant chunks ────────────────────────
    chunks = query_index(question, top_k=top_k)
    context_block = _build_context_block(chunks)

    # ── 3. Build messages (include conversation history) ───
    user_message = (
        f"Environment: {environment.upper()}\n\n"
        f"DOCUMENTATION CONTEXT:\n{context_block}\n\n"
        f"USER QUESTION:\n{question}"
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include last 6 turns of history for context
    for turn in conversation_history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_message})

    # ── 4. Call OpenAI ─────────────────────────────────────
    model     = os.environ.get("CHAT_MODEL", "gpt-4o-mini")
    max_tokens = int(os.environ.get("MAX_TOKENS", "1024"))

    llm_response = _openai.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,   # Low temp = factual, less creative / hallucinatory
        response_format={"type": "json_object"},
    )

    raw = llm_response.choices[0].message.content or ""
    parsed = _parse_llm_response(raw)

    # ── 5. Build final response ────────────────────────────
    sources = _build_sources(chunks)
    response_time_ms = int((time.time() - start) * 1000)

    result = {
        "answer":              parsed.get("answer", ""),
        "follow_up_questions": parsed.get("follow_up_questions", []),
        "sources":             sources,
        "confidence":          parsed.get("confidence", "medium"),
        "cached":              False,
        "response_time_ms":    response_time_ms,
    }

    # ── 6. Store in cache ──────────────────────────────────
    cache.set(cache_key, result, ttl=cache_ttl)

    # ── 7. Log to Supabase (fire-and-forget) ──────────────
    try:
        await log_interaction(
            session_id=session_id,
            user_id=user_id,
            question=question,
            answer=result["answer"],
            sources=sources,
            confidence=result["confidence"],
            response_time_ms=response_time_ms,
            environment=environment,
            chunks_retrieved=len(chunks),
        )
    except Exception as e:
        logger.warning(f"Supabase logging failed (non-fatal): {e}")

    return result
