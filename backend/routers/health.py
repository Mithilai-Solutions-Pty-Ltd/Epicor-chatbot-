"""
============================================================
Health Router – /api/health
============================================================
Used by:
  • Render health checks
  • cron-job.org keep-alive pings (prevents free-tier sleep)
  • Internal monitoring
============================================================
"""

import os
import time
import asyncio
import logging
from fastapi import APIRouter
from backend.services.cache_service import cache

logger = logging.getLogger("botzi.health")
router = APIRouter()

_startup_time = time.time()


@router.get("/health")
async def health_check():
    """
    Lightweight health endpoint.
    cron-job.org should ping this every 60 seconds to keep
    the Render free-tier instance awake 24/7.
    """
    uptime_seconds = int(time.time() - _startup_time)
    return {
        "status":   "healthy",
        "service":  "BOTZI",
        "env":      os.environ.get("APP_ENV", "production"),
        "uptime_s": uptime_seconds,
        "cache":    cache.stats(),
    }


@router.get("/ping")
async def ping():
    """Ultra-lightweight ping for keep-alive."""
    return {"pong": True}
