"""
============================================================
BOTZI - Epicor AI Support Chatbot
Backend: FastAPI + Supabase pgvector + OpenAI + Supabase
============================================================
SETUP STEPS:
1. pip install -r requirements.txt
2. Copy .env.example to .env and fill in all keys
3. Run: uvicorn backend.main:app --reload --port 8000
============================================================
"""

from dotenv import load_dotenv
load_dotenv()
import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Internal routers ──────────────────────────────────────
from backend.routers import chat, feedback, analytics, health, cliq
from backend.services.vector_service import init_pinecone
from backend.services.cache_service import cache
from backend.middleware.rate_limiter import RateLimitMiddleware

# ── Logging setup ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("botzi")


# ── Lifespan: runs once on startup / shutdown ─────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup."""
    logger.info("🚀 BOTZI starting up...")

    # Step 1 – Connect to Supabase pgvector
    try:
        init_pinecone()
        logger.info("✅ Supabase pgvector connected")
    except Exception as e:
        logger.error(f"❌ Supabase pgvector init failed: {e}")

    # Step 2 – Warm up in-memory cache
    cache.clear()
    logger.info("✅ Cache initialised")

    logger.info("🟢 BOTZI is ready for requests")
    yield

    # Shutdown cleanup
    logger.info("🔴 BOTZI shutting down")
    cache.clear()


# ── FastAPI app ───────────────────────────────────────────
app = FastAPI(
    title="BOTZI – Epicor AI Support Chatbot",
    description="Production-ready RAG chatbot for Epicor ERP support",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow Zoho Cliq widget + any frontend) ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting middleware ──────────────────────────────
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)


# ── Request timing middleware ─────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = round((time.time() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(process_time)
    return response


# ── Global error handler ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again."},
    )


# ── Mount routers ─────────────────────────────────────────
app.include_router(health.router,    prefix="/api",      tags=["Health"])
app.include_router(chat.router,      prefix="/api/chat", tags=["Chat"])
app.include_router(feedback.router,  prefix="/api",      tags=["Feedback"])
app.include_router(analytics.router, prefix="/api",      tags=["Analytics"])
app.include_router(cliq.router,      prefix="/api",      tags=["Zoho Cliq"])


# ── Root endpoint ─────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "BOTZI – Epicor AI Support Chatbot",
        "status": "running",
        "docs": "/docs",
    }
