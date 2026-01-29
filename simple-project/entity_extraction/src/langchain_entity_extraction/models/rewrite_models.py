"""Data models for question rewriting."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OriginalQuestion(BaseModel):
    """Original user question model.

    Represents the user's input question before rewriting.
    """

    content: str = Field(..., description="Question content")
    domain: Optional[str] = Field(
        None, description="Business domain (e.g., 'billing', 'product')"
    )
    context: Optional[str] = Field(
        None, description="Additional context information"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "content": "今年cdn产品金额是多少",
                "domain": "billing",
                "context": None
            }
        }


class RewrittenQuestion(BaseModel):
    """Rewritten question model.

    Represents the question after rewriting with explicit entities.
    """

    original: str = Field(..., description="Original question content")
    rewritten: str = Field(..., description="Rewritten question content")
    entities: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Rewrite confidence score"
    )
    reasoning: Optional[str] = Field(
        None, description="Reasoning process for the rewrite"
    )
    changes_made: List[str] = Field(
        default_factory=list, description="List of changes made"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "original": "今年cdn产品金额是多少",
                "rewritten": "产品ID为cdn，时间为2026年的出账金额是多少",
                "entities": {
                    "product_id": "cdn",
                    "time": "2026年",
                    "field": "出账金额"
                },
                "confidence": 0.95,
                "reasoning": "将'今年'转换为'2026年'，'cdn'转换为'产品ID为cdn'，'金额'转换为'出账金额'",
                "changes_made": [
                    "时间规范化: 今年 → 2026年",
                    "产品ID规范化: cdn → 产品ID为cdn",
                    "字段明确化: 金额 → 出账金额"
                ]
            }
        }


class RewriteResult(BaseModel):
    """Result of question rewriting operation.

    Contains the original question, rewritten question, and metadata.
    """

    success: bool = Field(..., description="Whether rewriting was successful")
    original: OriginalQuestion = Field(..., description="Original question")
    rewritten: Optional[RewrittenQuestion] = Field(
        None, description="Rewritten question (if successful)"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    processing_time_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "original": {
                    "content": "今年cdn产品金额是多少"
                },
                "rewritten": {
                    "original": "今年cdn产品金额是多少",
                    "rewritten": "产品ID为cdn，时间为2026年的出账金额是多少",
                    "entities": {
                        "product_id": "cdn",
                        "time": "2026年",
                        "field": "出账金额"
                    }
                },
                "errors": [],
                "processing_time_ms": 1234.5
            }
        }


class BatchRewriteResult(BaseModel):
    """Result of batch question rewriting operation."""

    results: List[RewriteResult] = Field(..., description="Individual rewrite results")
    total_count: int = Field(..., description="Total number of questions")
    successful_count: int = Field(default=0, description="Number of successful rewrites")
    failed_count: int = Field(default=0, description="Number of failed rewrites")
    total_time_ms: float = Field(..., description="Total processing time in milliseconds")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "results": [],
                "total_count": 10,
                "successful_count": 9,
                "failed_count": 1,
                "total_time_ms": 5000.0
            }
        }
