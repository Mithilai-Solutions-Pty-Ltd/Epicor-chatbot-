"""
============================================================
Supabase Service
============================================================
Tables used (SQL to create them is in scripts/supabase_setup.sql):

  1. chat_interactions  – every Q&A logged with timing
  2. feedback           – user ratings per session
  3. active_users       – rolling window of who used chatbot

All writes are async / fire-and-forget to avoid slowing chat.
============================================================
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from supabase import create_client, Client

logger = logging.getLogger("botzi.supabase")

_sb: Client | None = None


def get_supabase() -> Client:
    """Lazy-init Supabase client (singleton)."""
    global _sb
    if _sb is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _sb = create_client(url, key)
    return _sb


# ── Log every chat interaction ─────────────────────────────
async def log_interaction(
    session_id: str,
    user_id: str,
    question: str,
    answer: str,
    sources: List[Dict],
    confidence: str,
    response_time_ms: int,
    environment: str,
    chunks_retrieved: int,
) -> None:
    """Insert a row into chat_interactions."""
    try:
        sb = get_supabase()
        sb.table("chat_interactions").insert({
            "session_id":       session_id,
            "user_id":          user_id,
            "question":         question,
            "answer":           answer[:4000],    # avoid column overflow
            "sources":          sources,           # JSONB column
            "confidence":       confidence,
            "response_time_ms": response_time_ms,
            "environment":      environment,
            "chunks_retrieved": chunks_retrieved,
            "created_at":       datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"log_interaction failed: {e}")


# ── Log user feedback (star rating + comment) ──────────────
async def log_feedback(
    session_id: str,
    user_id: str,
    question: str,
    rating: int,         # 1-5 stars
    comment: str = "",
    helpful: Optional[bool] = None,
) -> None:
    """Insert a row into feedback table."""
    try:
        sb = get_supabase()
        sb.table("feedback").insert({
            "session_id": session_id,
            "user_id":    user_id,
            "question":   question,
            "rating":     rating,
            "comment":    comment,
            "helpful":    helpful,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"log_feedback failed: {e}")


# ── Analytics helpers ──────────────────────────────────────
def get_usage_summary(days: int = 7) -> Dict[str, Any]:
    """
    Return aggregated usage stats for the last N days.
    Used by the /api/analytics endpoint.
    """
    try:
        sb = get_supabase()

        # Total interactions
        total = sb.table("chat_interactions") \
                  .select("id", count="exact") \
                  .execute()

        # Avg response time
        avg_rt = sb.table("chat_interactions") \
                   .select("response_time_ms") \
                   .execute()
        times = [r["response_time_ms"] for r in (avg_rt.data or [])]
        avg_time = round(sum(times) / len(times)) if times else 0

        # Avg rating
        ratings = sb.table("feedback").select("rating").execute()
        r_vals = [r["rating"] for r in (ratings.data or [])]
        avg_rating = round(sum(r_vals) / len(r_vals), 2) if r_vals else 0

        # Unique users
        users = sb.table("chat_interactions") \
                  .select("user_id") \
                  .execute()
        unique_users = len(set(r["user_id"] for r in (users.data or [])))

        # High confidence %
        conf = sb.table("chat_interactions").select("confidence").execute()
        conf_data = [r["confidence"] for r in (conf.data or [])]
        high_pct = (
            round(conf_data.count("high") / len(conf_data) * 100, 1)
            if conf_data else 0
        )

        return {
            "total_interactions": total.count or 0,
            "unique_users":       unique_users,
            "avg_response_time_ms": avg_time,
            "avg_rating":         avg_rating,
            "high_confidence_pct": high_pct,
            "total_feedback":     len(r_vals),
        }
    except Exception as e:
        logger.error(f"get_usage_summary failed: {e}")
        return {}


def get_top_questions(limit: int = 10) -> List[Dict]:
    """Return the most frequently asked questions."""
    try:
        sb = get_supabase()
        result = sb.table("chat_interactions") \
                   .select("question") \
                   .limit(200) \
                   .execute()
        from collections import Counter
        q_counts = Counter(r["question"] for r in (result.data or []))
        return [{"question": q, "count": c}
                for q, c in q_counts.most_common(limit)]
    except Exception as e:
        logger.error(f"get_top_questions failed: {e}")
        return []
