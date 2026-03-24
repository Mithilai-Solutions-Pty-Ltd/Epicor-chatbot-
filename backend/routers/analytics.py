"""
============================================================
Analytics Router – /api/analytics
============================================================
"""
from fastapi import APIRouter
from backend.services.supabase_service import get_usage_summary, get_top_questions
from backend.services.cache_service import cache

router = APIRouter()


@router.get("/analytics/summary")
async def analytics_summary():
    """
    Return usage stats: total interactions, unique users,
    avg response time, avg rating, confidence breakdown.
    """
    summary = get_usage_summary()
    summary["cache_stats"] = cache.stats()
    return summary


@router.get("/analytics/top-questions")
async def top_questions(limit: int = 10):
    """Return the most frequently asked questions."""
    return {"questions": get_top_questions(limit=limit)}
