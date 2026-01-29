"""Extraction result models."""

from typing import Any, List, Optional, Type, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class ExtractionError(BaseModel):
    """Error information from extraction."""

    message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )


class ExtractionResult(BaseModel):
    """Result of an entity extraction operation."""

    entities: List[Any] = Field(
        default_factory=list, description="Extracted entities"
    )
    schema_type: Optional[str] = Field(
        None, description="Type of schema used for extraction"
    )
    success: bool = Field(
        default=True, description="Whether extraction was successful"
    )
    errors: List[ExtractionError] = Field(
        default_factory=list, description="List of errors during extraction"
    )
    text_length: int = Field(
        default=0, description="Length of input text"
    )
    extraction_time_ms: Optional[float] = Field(
        None, description="Time taken for extraction in milliseconds"
    )
    raw_output: Optional[Dict[str, Any]] = Field(
        None, description="Raw LLM output (if enabled)"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "entities": [
                    {"name": "John Smith", "age": 35, "title": "Software Engineer"}
                ],
                "schema_type": "PersonEntity",
                "success": True,
                "text_length": 150,
                "extraction_time_ms": 1234.5
            }
        }


class BatchExtractionResult(BaseModel):
    """Result of a batch extraction operation."""

    results: List[ExtractionResult] = Field(
        default_factory=list, description="Individual extraction results"
    )
    total_texts: int = Field(..., description="Total number of texts processed")
    successful_count: int = Field(default=0, description="Number of successful extractions")
    failed_count: int = Field(default=0, description="Number of failed extractions")
    total_entities: int = Field(default=0, description="Total entities extracted")
    total_time_ms: float = Field(..., description="Total time for batch extraction in milliseconds")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "results": [],
                "total_texts": 10,
                "successful_count": 9,
                "failed_count": 1,
                "total_entities": 25,
                "total_time_ms": 5000.0
            }
        }
