"""
============================================================
Feedback Router – /api/feedback
============================================================
"""
import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.services.supabase_service import log_feedback

logger = logging.getLogger("botzi.feedback")
router = APIRouter()


class FeedbackRequest(BaseModel):
    session_id: str
    user_id: str = "anonymous"
    question: str
    rating: int = Field(..., ge=1, le=5, description="1-5 star rating")
    comment: Optional[str] = ""
    helpful: Optional[bool] = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """
    Submit star rating + optional comment for a chatbot response.
    Stored in Supabase feedback table for continuous improvement.
    """
    await log_feedback(
        session_id=req.session_id,
        user_id=req.user_id,
        question=req.question,
        rating=req.rating,
        comment=req.comment or "",
        helpful=req.helpful,
    )
    return {"message": "Thank you for your feedback! It helps us improve BOTZI."}
