"""
LangChain Entity Extraction Package

A reference implementation for entity extraction using LangChain.

Includes:
- Entity extraction service (Person, Organization, Product, etc.)
- Question rewriting service for NL to SQL pipelines
"""

__version__ = "0.2.0"
__author__ = "Claude Code"

from langchain_entity_extraction.services.extraction_service import ExtractionService
from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
    LocationEntity,
    EventEntity,
)

# Question rewriting module
from langchain_entity_extraction.rewrite import (
    QuestionRewriter,
    TimeNormalizer,
    EntityMapper,
)

__all__ = [
    # Entity Extraction
    "ExtractionService",
    "PersonEntity",
    "OrganizationEntity",
    "ProductEntity",
    "LocationEntity",
    "EventEntity",
    # Question Rewriting
    "QuestionRewriter",
    "TimeNormalizer",
    "EntityMapper",
]
