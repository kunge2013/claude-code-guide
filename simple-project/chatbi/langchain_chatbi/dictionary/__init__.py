"""
Dictionary Module for ChatBI

Provides dictionary value transformation with caching and synonym support.
"""

from langchain_chatbi.dictionary.dictionary_service import (
    DictionaryService,
    get_dictionary_service,
)
from langchain_chatbi.dictionary.models import (
    DictionaryConfig,
    DictionaryEntry,
    DictionaryDefinition,
    SynonymGroup,
    TransformationResult,
)

__all__ = [
    "DictionaryService",
    "get_dictionary_service",
    "DictionaryConfig",
    "DictionaryEntry",
    "DictionaryDefinition",
    "SynonymGroup",
    "TransformationResult",
]
