"""High-level extraction service for entity extraction."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Type, Union

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from langchain_entity_extraction.config.settings import get_settings
from langchain_entity_extraction.extractors.base_extractor import BaseExtractor
from langchain_entity_extraction.extractors.schema_extractor import SchemaExtractor
from langchain_entity_extraction.extractors.pydantic_extractor import PydanticExtractor
from langchain_entity_extraction.extractors.relation_extractor import RelationExtractor
from langchain_entity_extraction.llm.langchain_llm import create_langchain_llm
from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
    LocationEntity,
    EventEntity,
    EntityRelationship,
)
from langchain_entity_extraction.models.extraction_result import (
    ExtractionResult,
    BatchExtractionResult,
)
from langchain_entity_extraction.utils.logger import setup_logger, get_logger

# Setup logger
setup_logger()
logger = get_logger(__name__)


class ExtractionService:
    """
    High-level service for entity extraction operations.

    Provides a unified interface for extracting various types of
    entities from text using LangChain.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        strategy: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the extraction service.

        Args:
            llm: Optional LangChain LLM instance (created from config if not provided)
            strategy: Extraction strategy (pydantic, schema, hybrid)
            config: Optional configuration dictionary
        """
        self.settings = get_settings()
        self.config = config or self.settings.config

        # Determine strategy
        if strategy is None:
            strategy = self.settings.extraction_strategy

        # Create LLM if not provided
        if llm is None:
            llm = create_langchain_llm()

        self.llm = llm
        self.strategy = strategy

        # Initialize extractors based on strategy
        self._init_extractors()

        logger.info(
            f"ExtractionService initialized",
            strategy=strategy,
            llm_type=type(llm).__name__
        )

    def _init_extractors(self) -> None:
        """Initialize extractors based on strategy."""
        # Always create Pydantic extractor (recommended)
        self.pydantic_extractor = PydanticExtractor(
            self.llm,
            self.config
        )

        # Create schema extractor if needed
        if self.strategy in ("schema", "hybrid"):
            self.schema_extractor = SchemaExtractor(
                self.llm,
                self.config
            )
        else:
            self.schema_extractor = None

        # Create relation extractor
        self.relation_extractor = RelationExtractor(
            self.llm,
            self.config
        )

    async def extract_persons(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[PersonEntity]:
        """
        Extract person entities from text.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction instead of Pydantic

        Returns:
            List of PersonEntity objects

        Example:
            >>> service = ExtractionService()
            >>> text = "John Smith is a 35-year-old software engineer at Google."
            >>> persons = await service.extract_persons(text)
            >>> print(persons[0].name)  # "John Smith"
        """
        if use_schema and self.schema_extractor:
            result = await self.schema_extractor.extract(
                text,
                self.settings.get("entity_types.person.schema")
            )
            return [PersonEntity(**e) for e in result.entities]
        else:
            result = await self.pydantic_extractor.extract(text, PersonEntity)
            return result.entities

    async def extract_organizations(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[OrganizationEntity]:
        """
        Extract organization entities from text.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction instead of Pydantic

        Returns:
            List of OrganizationEntity objects
        """
        if use_schema and self.schema_extractor:
            result = await self.schema_extractor.extract(
                text,
                self.settings.get("entity_types.organization.schema")
            )
            return [OrganizationEntity(**e) for e in result.entities]
        else:
            result = await self.pydantic_extractor.extract(text, OrganizationEntity)
            return result.entities

    async def extract_products(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[ProductEntity]:
        """
        Extract product entities from text.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction instead of Pydantic

        Returns:
            List of ProductEntity objects
        """
        if use_schema and self.schema_extractor:
            result = await self.schema_extractor.extract(
                text,
                self.settings.get("entity_types.product.schema")
            )
            return [ProductEntity(**e) for e in result.entities]
        else:
            result = await self.pydantic_extractor.extract(text, ProductEntity)
            return result.entities

    async def extract_locations(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[LocationEntity]:
        """
        Extract location entities from text.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction instead of Pydantic

        Returns:
            List of LocationEntity objects
        """
        if use_schema and self.schema_extractor:
            result = await self.schema_extractor.extract(
                text,
                self.settings.get("entity_types.location.schema")
            )
            return [LocationEntity(**e) for e in result.entities]
        else:
            result = await self.pydantic_extractor.extract(text, LocationEntity)
            return result.entities

    async def extract_events(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[EventEntity]:
        """
        Extract event entities from text.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction instead of Pydantic

        Returns:
            List of EventEntity objects
        """
        if use_schema and self.schema_extractor:
            result = await self.schema_extractor.extract(
                text,
                self.settings.get("entity_types.event.schema")
            )
            return [EventEntity(**e) for e in result.entities]
        else:
            result = await self.pydantic_extractor.extract(text, EventEntity)
            return result.entities

    async def extract_relations(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[EntityRelationship]:
        """
        Extract relationships between entities from text.

        Args:
            text: Input text to extract from
            entity_types: Optional list of entity types to look for

        Returns:
            List of EntityRelationship objects
        """
        result = await self.relation_extractor.extract(text, entity_types)
        return result.entities

    async def extract_all(
        self,
        text: str,
        use_schema: bool = False
    ) -> Dict[str, List[BaseModel]]:
        """
        Extract all entity types from text.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction instead of Pydantic

        Returns:
            Dictionary mapping entity type names to lists of entities

        Example:
            >>> service = ExtractionService()
            >>> text = "John Smith works at Google in Mountain View, CA."
            >>> entities = await service.extract_all(text)
            >>> print(entities['persons'])  # [PersonEntity(name='John Smith')]
            >>> print(entities['organizations'])  # [OrganizationEntity(name='Google')]
            >>> print(entities['locations'])  # [LocationEntity(name='Mountain View')]
        """
        logger.info(f"Extracting all entity types from text (length={len(text)})")

        # Extract all entity types in parallel
        results = await asyncio.gather(
            self.extract_persons(text, use_schema),
            self.extract_organizations(text, use_schema),
            self.extract_products(text, use_schema),
            self.extract_locations(text, use_schema),
            self.extract_events(text, use_schema),
            return_exceptions=True
        )

        # Combine results
        return {
            "persons": results[0] if not isinstance(results[0], Exception) else [],
            "organizations": results[1] if not isinstance(results[1], Exception) else [],
            "products": results[2] if not isinstance(results[2], Exception) else [],
            "locations": results[3] if not isinstance(results[3], Exception) else [],
            "events": results[4] if not isinstance(results[4], Exception) else [],
        }

    async def extract_batch(
        self,
        texts: List[str],
        schema: Union[Type[BaseModel], Dict[str, Any]],
        max_concurrency: int = 5
    ) -> BatchExtractionResult:
        """
        Extract entities from multiple texts in batch.

        Args:
            texts: List of input texts
            schema: Schema to use for extraction (Pydantic model or dict)
            max_concurrency: Maximum number of concurrent extractions

        Returns:
            BatchExtractionResult with all extraction results
        """
        start_time = time.time()
        total_texts = len(texts)

        logger.info(
            f"Starting batch extraction",
            total_texts=total_texts,
            max_concurrency=max_concurrency
        )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)

        async def extract_with_limit(text: str, index: int) -> ExtractionResult:
            async with semaphore:
                if isinstance(schema, type) and issubclass(schema, BaseModel):
                    result = await self.pydantic_extractor.extract(text, schema)
                else:
                    result = await self.schema_extractor.extract(text, schema)
                return result

        # Run extractions with concurrency limit
        tasks = [
            extract_with_limit(text, i)
            for i, text in enumerate(texts)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_count = 0
        failed_count = 0
        total_entities = 0
        extraction_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                extraction_results.append(
                    ExtractionResult(
                        entities=[],
                        success=False,
                        text_length=len(texts[i])
                    )
                )
            elif result.success:
                successful_count += 1
                total_entities += len(result.entities)
                extraction_results.append(result)
            else:
                failed_count += 1
                extraction_results.append(result)

        total_time_ms = (time.time() - start_time) * 1000

        batch_result = BatchExtractionResult(
            results=extraction_results,
            total_texts=total_texts,
            successful_count=successful_count,
            failed_count=failed_count,
            total_entities=total_entities,
            total_time_ms=total_time_ms
        )

        logger.info(
            f"Batch extraction completed",
            successful=successful_count,
            failed=failed_count,
            total_entities=total_entities,
            time_ms=total_time_ms
        )

        return batch_result

    async def extract_with_custom_schema(
        self,
        text: str,
        schema: Union[Type[BaseModel], Dict[str, Any]]
    ) -> List[BaseModel]:
        """
        Extract entities using a custom schema.

        Args:
            text: Input text to extract from
            schema: Custom Pydantic model or dictionary schema

        Returns:
            List of extracted entities
        """
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            result = await self.pydantic_extractor.extract(text, schema)
        else:
            result = await self.schema_extractor.extract(text, schema)

        return result.entities

    def extract_persons_sync(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[PersonEntity]:
        """
        Synchronous wrapper for extract_persons.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction

        Returns:
            List of PersonEntity objects
        """
        return asyncio.run(self.extract_persons(text, use_schema))

    def extract_all_sync(
        self,
        text: str,
        use_schema: bool = False
    ) -> Dict[str, List[BaseModel]]:
        """
        Synchronous wrapper for extract_all.

        Args:
            text: Input text to extract from
            use_schema: If True, use schema-based extraction

        Returns:
            Dictionary mapping entity type names to lists of entities
        """
        return asyncio.run(self.extract_all(text, use_schema))
