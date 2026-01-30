"""
Entity Extraction API Endpoints.

Separate module for extraction-related endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract", tags=["extraction"])


class ExtractRequest(BaseModel):
    """Request for entity extraction."""
    text: str = Field(..., description="Input text to extract entities from")
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Specific entity types to extract"
    )


class ExtractResponse(BaseModel):
    """Response for entity extraction."""
    success: bool
    text: str
    entities: Dict[str, List[Dict]]
    processing_time_ms: float
    errors: List[str] = []


@router.post("/", response_model=ExtractResponse)
async def extract_entities(request: ExtractRequest):
    """Extract entities from text."""
    import time
    from langchain_entity_extraction.small_model.services.small_extraction_service import SmallExtractionService

    start_time = time.time()

    try:
        service = SmallExtractionService()

        if request.entity_types:
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
        else:
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
        raise HTTPException(status_code=500, detail=str(e))
