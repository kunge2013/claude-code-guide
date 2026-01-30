"""
FastAPI Application for Small Model Services.

REST API for entity extraction and question rewriting.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

# Import services
from langchain_entity_extraction.small_model.services.small_extraction_service import SmallExtractionService
from langchain_entity_extraction.small_model.services.small_rewrite_service import SmallRewriteService
from langchain_entity_extraction.small_model.services.hybrid_service import HybridService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Small Model Entity Extraction & Question Rewrite API",
    description="Fast API services for entity extraction and question rewriting using BERT and T5 models",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instances
_extraction_service = None
_rewrite_service = None
_hybrid_service = None


def get_extraction_service():
    """Get or create extraction service instance."""
    global _extraction_service
    if _extraction_service is None:
        logger.info("Initializing SmallExtractionService...")
        _extraction_service = SmallExtractionService(
            model_path="models/ner_bert",
            use_hybrid=False
        )
    return _extraction_service


def get_rewrite_service():
    """Get or create rewrite service instance."""
    global _rewrite_service
    if _rewrite_service is None:
        logger.info("Initializing SmallRewriteService...")
        _rewrite_service = SmallRewriteService(
            model_path="models/rewrite_t5",
            ner_model_path="models/ner_bert"
        )
    return _rewrite_service


def get_hybrid_service():
    """Get or create hybrid service instance."""
    global _hybrid_service
    if _hybrid_service is None:
        logger.info("Initializing HybridService...")
        _hybrid_service = HybridService(
            ner_model_path="models/ner_bert",
            t5_model_path="models/rewrite_t5"
        )
    return _hybrid_service


# ===== Request/Response Models =====

class ExtractRequest(BaseModel):
    """Request for entity extraction."""
    text: str = Field(..., description="Input text to extract entities from")
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Specific entity types to extract (persons, organizations, products, locations, events)"
    )


class ExtractResponse(BaseModel):
    """Response for entity extraction."""
    success: bool
    text: str
    entities: Dict[str, List[Dict]]
    processing_time_ms: float
    errors: List[str] = []


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


class BatchExtractRequest(BaseModel):
    """Request for batch entity extraction."""
    texts: List[str] = Field(..., description="List of input texts")


class BatchRewriteRequest(BaseModel):
    """Request for batch question rewriting."""
    questions: List[str] = Field(..., description="List of questions to rewrite")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: Dict[str, str]


# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Small Model API...")


# ===== Health Check =====

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        services={
            "extraction": "ready",
            "rewrite": "ready",
            "hybrid": "ready"
        }
    )


# ===== Entity Extraction Endpoints =====

@app.post("/extract", response_model=ExtractResponse)
async def extract_entities(request: ExtractRequest):
    """
    Extract entities from text.

    Extracts persons, organizations, products, locations, and events from input text.
    """
    import time
    start_time = time.time()

    try:
        service = get_extraction_service()

        if request.entity_types:
            # Extract specific types
            entities = {}
            for entity_type in request.entity_types:
                if entity_type == "persons":
                    entities["persons"] = [
                        e.model_dump() for e in await service.extract_persons(request.text)
                    ]
                elif entity_type == "organizations":
                    entities["organizations"] = [
                        e.model_dump() for e in await service.extract_organizations(request.text)
                    ]
                elif entity_type == "products":
                    entities["products"] = [
                        e.model_dump() for e in await service.extract_products(request.text)
                    ]
                elif entity_type == "locations":
                    entities["locations"] = [
                        e.model_dump() for e in await service.extract_locations(request.text)
                    ]
                elif entity_type == "events":
                    entities["events"] = [
                        e.model_dump() for e in await service.extract_events(request.text)
                    ]
        else:
            # Extract all types
            all_entities = await service.extract_all(request.text)
            entities = {
                k: [e.model_dump() if hasattr(e, 'model_dump') else e for e in v]
                for k, v in all_entities.items()
            }

        processing_time_ms = (time.time() - start_time) * 1000

        return ExtractResponse(
            success=True,
            text=request.text,
            entities=entities,
            processing_time_ms=processing_time_ms
        )

    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        logger.error(f"Extraction error: {str(e)}")
        return ExtractResponse(
            success=False,
            text=request.text,
            entities={},
            processing_time_ms=processing_time_ms,
            errors=[str(e)]
        )


# ===== Question Rewrite Endpoints =====

@app.post("/rewrite", response_model=RewriteResponse)
async def rewrite_question(request: RewriteRequest):
    """
    Rewrite a question.

    Rewrites natural language questions to be more structured and explicit.
    """
    import time
    start_time = time.time()

    try:
        service = get_rewrite_service()

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
        return RewriteResponse(
            success=False,
            original=request.question,
            rewritten=None,
            entities=None,
            confidence=None,
            processing_time_ms=processing_time_ms,
            errors=[str(e)]
        )


# ===== Combined Endpoint =====

@app.post("/process")
async def extract_and_rewrite(text: str):
    """
    Extract entities AND rewrite the question in one call.

    Args:
        text: Input text/question

    Returns:
        Combined result with both extraction and rewrite
    """
    import time
    start_time = time.time()

    try:
        extraction_service = get_extraction_service()
        rewrite_service = get_rewrite_service()

        # Extract entities
        entities = await extraction_service.extract_all(text)

        # Rewrite question
        rewrite_result = await rewrite_service.rewrite(text)

        processing_time_ms = (time.time() - start_time) * 1000

        return {
            "success": True,
            "original": text,
            "entities": {
                k: [e.model_dump() if hasattr(e, 'model_dump') else e for e in v]
                for k, v in entities.items()
            },
            "rewritten": rewrite_result.rewritten.rewritten if rewrite_result.rewritten else text,
            "processing_time_ms": processing_time_ms
        }

    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        logger.error(f"Process error: {str(e)}")
        return {
            "success": False,
            "original": text,
            "entities": {},
            "rewritten": text,
            "processing_time_ms": processing_time_ms,
            "errors": [str(e)]
        }


# ===== Hybrid Service Endpoints =====

@app.post("/hybrid/extract")
async def hybrid_extract(text: str, entity_type: str):
    """
    Extract entities using hybrid service (intelligent routing).

    Routes between small model and LLM based on confidence.
    """
    import time
    start_time = time.time()

    try:
        service = get_hybrid_service()

        if entity_type == "persons":
            entities = await service.extract_persons(text)
        elif entity_type == "organizations":
            entities = await service.extract_organizations(text)
        elif entity_type == "products":
            entities = await service.extract_products(text)
        elif entity_type == "locations":
            entities = await service.extract_locations(text)
        else:
            entities = await service.extract_all(text)

        processing_time_ms = (time.time() - start_time) * 1000

        return {
            "success": True,
            "entities": [e.model_dump() if hasattr(e, 'model_dump') else e for e in entities]
            if isinstance(entities, list) else entities,
            "stats": service.get_stats(),
            "processing_time_ms": processing_time_ms
        }

    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "entities": [],
            "processing_time_ms": processing_time_ms,
            "errors": [str(e)]
        }


@app.post("/hybrid/rewrite")
async def hybrid_rewrite(question: str, context: Optional[Dict] = None):
    """
    Rewrite question using hybrid service (intelligent routing).

    Routes between small model and LLM based on confidence.
    """
    import time
    start_time = time.time()

    try:
        service = get_hybrid_service()

        result = await service.rewrite(question, context)

        processing_time_ms = (time.time() - start_time) * 1000

        return {
            "success": result.success,
            "original": result.original.content,
            "rewritten": result.rewritten.rewritten if result.rewritten else None,
            "entities": result.rewritten.entities if result.rewritten else None,
            "confidence": result.rewritten.confidence if result.rewritten else None,
            "stats": service.get_stats(),
            "processing_time_ms": processing_time_ms
        }

    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "original": question,
            "rewritten": None,
            "processing_time_ms": processing_time_ms,
            "errors": [str(e)]
        }


# ===== Statistics Endpoints =====

@app.get("/stats")
async def get_stats():
    """Get hybrid service statistics."""
    service = get_hybrid_service()
    return service.get_stats()


@app.post("/stats/reset")
async def reset_stats():
    """Reset hybrid service statistics."""
    service = get_hybrid_service()
    service.reset_stats()
    return {"message": "Statistics reset"}


# ===== Root Endpoint =====

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Small Model API",
        "version": "1.0.0",
        "description": "Fast API for entity extraction and question rewriting",
        "endpoints": {
            "health": "/health",
            "extract": "/extract",
            "rewrite": "/rewrite",
            "process": "/process",
            "hybrid_extract": "/hybrid/extract",
            "hybrid_rewrite": "/hybrid/rewrite",
            "stats": "/stats"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
