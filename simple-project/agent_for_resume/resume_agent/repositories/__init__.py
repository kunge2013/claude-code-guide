"""
Data repositories for knowledge base access.

This module provides data access layer abstractions for different storage backends.
"""

from .milvus_repository import MilvusRepository

__all__ = ["MilvusRepository"]
