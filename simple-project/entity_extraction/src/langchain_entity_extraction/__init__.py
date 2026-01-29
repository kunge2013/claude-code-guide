"""
LangChain Entity Extraction Package

A reference implementation for entity extraction using LangChain.
"""

__version__ = "0.1.0"
__author__ = "Claude Code"

from langchain_entity_extraction.services.extraction_service import ExtractionService
from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
    LocationEntity,
    EventEntity,
)

__all__ = [
    "ExtractionService",
    "PersonEntity",
    "OrganizationEntity",
    "ProductEntity",
    "LocationEntity",
    "EventEntity",
]
