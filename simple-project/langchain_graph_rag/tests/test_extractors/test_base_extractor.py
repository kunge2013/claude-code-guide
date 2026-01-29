"""
Tests for base extractor.
"""

import pytest
from src.langchain_graph_rag.extractors.base_extractor import BaseExtractor


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def validate_connection(self) -> bool:
        return True

    async def extract_tables(self):
        return []

    async def extract_relations(self):
        return []


def test_base_extractor_init():
    """Test base extractor initialization."""
    extractor = MockExtractor(name="test", config={"key": "value"})
    assert extractor.name == "test"
    assert extractor.get_config("key") == "value"
    assert extractor.get_config("missing") is None


def test_base_extractor_config():
    """Test configuration methods."""
    extractor = MockExtractor(name="test", config={"key1": "value1"})

    assert extractor.get_config("key1") == "value1"
    assert extractor.get_config("key2", "default") == "default"


def test_base_extractor_repr():
    """Test string representation."""
    extractor = MockExtractor(name="test_extractor")
    assert repr(extractor) == "MockExtractor(name='test_extractor')"
