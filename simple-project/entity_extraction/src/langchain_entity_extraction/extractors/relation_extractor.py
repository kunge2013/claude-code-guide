"""Relationship extractor for entity relationships."""

import time
from typing import Any, Dict, List

from langchain.chains import create_extraction_chain_pydantic
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from langchain_entity_extraction.extractors.base_extractor import BaseExtractor
from langchain_entity_extraction.models.entity_schemas import EntityRelationship
from langchain_entity_extraction.models.extraction_result import ExtractionResult
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class RelationExtractor(BaseExtractor):
    """
    Extractor for relationships between entities.

    Specialized extractor that identifies and extracts relationships
    between entities mentioned in the text.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the relation extractor.

        Args:
            llm: LangChain LLM instance
            config: Optional configuration dictionary
        """
        super().__init__(llm, config)
        self.logger.info("Initialized RelationExtractor")

        # Get configured relationship types
        self.relation_types = config.get(
            "relation_types",
            [
                "works_at",
                "located_in",
                "founded_by",
                "owns",
                "participates_in",
                "related_to",
                "knows",
                "manages"
            ]
        )

    async def extract(
        self,
        text: str,
        entity_types: List[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract relationships between entities from text.

        Args:
            text: Input text to extract relationships from
            entity_types: Optional list of entity types to look for
            **kwargs: Additional parameters

        Returns:
            ExtractionResult containing EntityRelationship objects

        Example:
            >>> text = "John Smith works at Google as a software engineer."
            >>> result = await extractor.extract(text)
        """
        start_time = time.time()
        text_length = len(text)

        try:
            self.logger.debug(
                f"Starting relationship extraction",
                text_length=text_length,
                entity_types=entity_types
            )

            # Create extraction chain with EntityRelationship schema
            chain = create_extraction_chain_pydantic(
                pydantic_schema=EntityRelationship,
                llm=self.llm
            )

            # Run extraction
            verbose = kwargs.get("verbose", False)
            result = await chain.ainvoke(
                {"input": [text]},
                {"verbose": verbose}
            )

            # Extract relationships from result
            relationships = self._parse_result(result)

            # Filter by entity types if specified
            if entity_types:
                relationships = self._filter_by_entity_types(
                    relationships, entity_types
                )

            extraction_time_ms = self._measure_time(start_time)

            self.logger.info(
                f"Relationship extraction completed",
                relationship_count=len(relationships),
                time_ms=extraction_time_ms
            )

            return self._create_result(
                entities=relationships,
                schema_type="EntityRelationship",
                text_length=text_length,
                extraction_time_ms=extraction_time_ms,
                raw_output=result if self.config.get("include_raw_output") else None
            )

        except Exception as e:
            self.logger.error(f"Relationship extraction failed: {str(e)}")
            return self.handle_error(
                e,
                {
                    "text_length": text_length,
                    "entity_types": entity_types
                }
            )

    def _parse_result(self, result: Dict[str, Any]) -> List[EntityRelationship]:
        """
        Parse the extraction chain result.

        Args:
            result: Raw result from extraction chain

        Returns:
            List of EntityRelationship objects
        """
        # Similar parsing logic to PydanticExtractor
        if isinstance(result, dict):
            if "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    return data
                return [data]

            for key, value in result.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], EntityRelationship):
                        return value

        if isinstance(result, list):
            return result

        self.logger.warning(f"Unexpected result format: {type(result)}")
        return []

    def _filter_by_entity_types(
        self,
        relationships: List[EntityRelationship],
        entity_types: List[str]
    ) -> List[EntityRelationship]:
        """
        Filter relationships by entity types.

        Args:
            relationships: List of relationships to filter
            entity_types: Entity types to keep

        Returns:
            Filtered list of relationships
        """
        # This is a placeholder for entity type filtering logic
        # In a real implementation, you would need to check
        # if the source/target entities match the specified types
        return relationships

    async def extract_with_context(
        self,
        text: str,
        known_entities: Dict[str, str],
        **kwargs
    ) -> ExtractionResult:
        """
        Extract relationships with known entity context.

        Args:
            text: Input text to extract relationships from
            known_entities: Dictionary mapping entity names to types
            **kwargs: Additional parameters

        Returns:
            ExtractionResult containing EntityRelationship objects
        """
        # Augment the extraction with known entity context
        start_time = time.time()
        text_length = len(text)

        try:
            # Create a custom prompt that includes known entities
            context_str = "\n".join(
                f"- {name}: {etype}"
                for name, etype in known_entities.items()
            )

            augmented_text = f"""Known entities:
{context_str}

Text to analyze:
{text}"""

            return await self.extract(augmented_text, **kwargs)

        except Exception as e:
            self.logger.error(f"Contextual relationship extraction failed: {str(e)}")
            return self.handle_error(
                e,
                {
                    "text_length": text_length,
                    "known_entities": known_entities
                }
            )
