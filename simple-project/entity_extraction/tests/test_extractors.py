"""Tests for entity extractors."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from langchain_entity_extraction.extractors.schema_extractor import SchemaExtractor
from langchain_entity_extraction.extractors.pydantic_extractor import PydanticExtractor
from langchain_entity_extraction.extractors.relation_extractor import RelationExtractor
from langchain_entity_extraction.models.entity_schemas import PersonEntity


@pytest.mark.asyncio
class TestSchemaExtractor:
    """Tests for SchemaExtractor."""

    async def test_extract_persons_with_schema(self):
        """Test extracting persons using schema."""
        mock_llm = Mock()
        mock_chain = Mock()
        mock_chain.ainvoke = AsyncMock(return_value={
            "data": [
                {"name": "John", "age": 30},
                {"name": "Jane", "age": 25}
            ]
        })

        with patch('langchain_entity_extraction.extractors.schema_extractor.create_extraction_chain') as mock_create:
            mock_create.return_value = mock_chain

            extractor = SchemaExtractor(mock_llm)
            result = await extractor.extract(
                "John is 30 and Jane is 25",
                {
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    },
                    "required": ["name"]
                }
            )

            assert result.success
            assert len(result.entities) == 2
            assert result.entities[0]["name"] == "John"
            assert result.entities[1]["name"] == "Jane"


@pytest.mark.asyncio
class TestPydanticExtractor:
    """Tests for PydanticExtractor."""

    async def test_extract_persons_with_pydantic(self):
        """Test extracting persons using Pydantic model."""
        mock_llm = Mock()
        mock_chain = Mock()
        mock_chain.ainvoke = AsyncMock(return_value={
            "data": [
                PersonEntity(name="John", age=30, title="Engineer"),
                PersonEntity(name="Jane", age=25, title="Manager")
            ]
        })

        with patch('langchain_entity_extraction.extractors.pydantic_extractor.create_extraction_chain_pydantic') as mock_create:
            mock_create.return_value = mock_chain

            extractor = PydanticExtractor(mock_llm)
            result = await extractor.extract(
                "John is a 30-year-old engineer. Jane is a 25-year-old manager.",
                PersonEntity
            )

            assert result.success
            assert len(result.entities) == 2
            assert result.entities[0].name == "John"
            assert result.entities[1].name == "Jane"


@pytest.mark.asyncio
class TestRelationExtractor:
    """Tests for RelationExtractor."""

    async def test_extract_relationships(self):
        """Test extracting relationships."""
        mock_llm = Mock()
        mock_chain = Mock()
        mock_chain.ainvoke = AsyncMock(return_value={
            "data": [
                {
                    "source_entity": "John",
                    "target_entity": "Google",
                    "relationship_type": "works_at"
                }
            ]
        })

        with patch('langchain_entity_extraction.extractors.relation_extractor.create_extraction_chain_pydantic') as mock_create:
            mock_create.return_value = mock_chain

            extractor = RelationExtractor(mock_llm)
            result = await extractor.extract("John works at Google")

            assert result.success
            assert len(result.entities) == 1
            assert result.entities[0].source_entity == "John"
            assert result.entities[0].target_entity == "Google"
