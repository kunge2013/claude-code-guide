"""
Small Model Solution for Entity Extraction and Question Rewrite.

This module provides a complete implementation of BERT-based NER
and T5-based question rewriting, designed to be independent from
the existing LLM-based solution.

Example:
    >>> from langchain_entity_extraction.small_model.services import SmallExtractionService
    >>> service = SmallExtractionService()
    >>> persons = await service.extract_persons("张三是阿里巴巴的工程师")
"""

from langchain_entity_extraction.small_model.services.small_extraction_service import SmallExtractionService
from langchain_entity_extraction.small_model.services.small_rewrite_service import SmallRewriteService
from langchain_entity_extraction.small_model.services.hybrid_service import HybridService

__all__ = [
    "SmallExtractionService",
    "SmallRewriteService",
    "HybridService",
]
