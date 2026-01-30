"""
Question Rewrite API Endpoints.

Separate module for rewrite-related endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rewrite", tags=["rewrite"])


class RewriteRequest(BaseModel):
    """Request for question rewriting."""
    question: str = Field(..., description="Original question to rewrite")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")
    use_simple_prompt: bool = Field(default=False, description="Whether to use simple prompt")


class RewriteResponse(BaseModel):
    """Response for question rewriting."""
    success: bool
    original: str
    rewritten: Optional[str]
    entities: Optional[Dict[str, Any]]
    confidence: Optional[float]
    processing_time_ms: float
    errors: List[str] = []


@router.post("/", response_model=RewriteResponse)
async def rewrite_question(request: RewriteRequest):
    """Rewrite a question."""
    import time
    from langchain_entity_extraction.small_model.services.small_rewrite_service import SmallRewriteService

    start_time = time.time()

    try:
        service = SmallRewriteService()

        result = await service.rewrite(
            request.question,
            request.context,
            request.use_simple_prompt
        )

        return RewriteResponse(
            success=result.success,
            original=result.original.content,
            rewritten=result.rewritten.rewritten if result.rewritten else None,
            entities=result.rewritten.entities if result.rewritten else None,
            confidence=result.rewritten.confidence if result.rewritten else None,
            processing_time_ms=result.processing_time_ms or 0,
            errors=result.errors
        )

    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        logger.error(f"Rewrite error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
