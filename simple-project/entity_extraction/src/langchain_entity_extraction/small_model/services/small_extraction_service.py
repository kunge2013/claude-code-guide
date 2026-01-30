"""
Small Model Entity Extraction Service.

Provides entity extraction using BERT-based NER model.
Interface compatible with existing ExtractionService.
"""

import time
from typing import List, Dict, Any, Optional, Type

from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
    LocationEntity,
    EventEntity,
)
from langchain_entity_extraction.models.extraction_result import (
    ExtractionResult,
    BatchExtractionResult,
)
from langchain_entity_extraction.small_model.models.ner_model import EntityRecognitionModel
from langchain_entity_extraction.small_model.utils.rule_normalizer import RuleNormalizer
from langchain_entity_extraction.small_model.config.ner_config import NERConfig


class SmallExtractionService:
    """
    Small model entity extraction service.

    Uses BERT-based NER model for fast, local entity extraction.
    Interface compatible with existing ExtractionService.

    Example:
        >>> service = SmallExtractionService()
        >>> persons = await service.extract_persons("张三是阿里巴巴的工程师")
        >>> products = await service.extract_products("cdn和ecs产品都很好用")
    """

    def __init__(
        self,
        model_path: str = "models/ner_bert",
        config: Optional[NERConfig] = None,
        use_hybrid: bool = False
    ):
        """
        Initialize the extraction service.

        Args:
            model_path: Path to trained NER model
            config: NER configuration (optional)
            use_hybrid: Whether to use hybrid mode (small model + LLM fallback)
        """
        self.config = config or NERConfig()
        self.use_hybrid = use_hybrid

        # Initialize NER model
        self.ner_model = EntityRecognitionModel(model_path, self.config)

        # Initialize normalizer
        self.normalizer = RuleNormalizer()

        # Hybrid mode: initialize LLM fallback
        self.llm_service = None
        if use_hybrid:
            try:
                from langchain_entity_extraction.services.extraction_service import ExtractionService
                self.llm_service = ExtractionService()
            except ImportError:
                self.use_hybrid = False

    async def extract_persons(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[PersonEntity]:
        """
        Extract person entities from text.

        Args:
            text: Input text
            use_schema: Whether to use schema-based extraction

        Returns:
            List of PersonEntity objects
        """
        entities = await self._extract_entities(text, entity_type="PERSON")

        # Convert to PersonEntity
        persons = []
        for entity in entities:
            persons.append(PersonEntity(
                name=entity["entity"],
                age=None,
                title=None,
                organization=None,
                email=None,
                phone=None,
                skills=[]
            ))

        return persons

    async def extract_organizations(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[OrganizationEntity]:
        """
        Extract organization entities from text.

        Args:
            text: Input text
            use_schema: Whether to use schema-based extraction

        Returns:
            List of OrganizationEntity objects
        """
        entities = await self._extract_entities(text, entity_type="ORG")

        organizations = []
        for entity in entities:
            organizations.append(OrganizationEntity(
                name=entity["entity"],
                industry=None,
                founded_year=None,
                headquarters=None,
                website=None
            ))

        return organizations

    async def extract_products(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[ProductEntity]:
        """
        Extract product entities from text.

        Args:
            text: Input text
            use_schema: Whether to use schema-based extraction

        Returns:
            List of ProductEntity objects
        """
        entities = await self._extract_entities(text, entity_type="PRODUCT")

        products = []
        for entity in entities:
            products.append(ProductEntity(
                name=entity["entity"],
                price=None,
                currency=None,
                category=None,
                features=[],
                manufacturer=None
            ))

        return products

    async def extract_locations(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[LocationEntity]:
        """
        Extract location entities from text.

        Args:
            text: Input text
            use_schema: Whether to use schema-based extraction

        Returns:
            List of LocationEntity objects
        """
        entities = await self._extract_entities(text, entity_type="LOCATION")

        locations = []
        for entity in entities:
            locations.append(LocationEntity(
                name=entity["entity"],
                type=None,
                country=None,
                region=None
            ))

        return locations

    async def extract_events(
        self,
        text: str,
        use_schema: bool = False
    ) -> List[EventEntity]:
        """
        Extract event entities from text.

        Args:
            text: Input text
            use_schema: Whether to use schema-based extraction

        Returns:
            List of EventEntity objects
        """
        # Events not typically extracted by NER, return empty
        return []

    async def extract_all(
        self,
        text: str,
        use_schema: bool = False
    ) -> Dict[str, List]:
        """
        Extract all entity types from text.

        Args:
            text: Input text
            use_schema: Whether to use schema-based extraction

        Returns:
            Dict with lists of different entity types
        """
        return {
            "persons": await self.extract_persons(text, use_schema),
            "organizations": await self.extract_organizations(text, use_schema),
            "products": await self.extract_products(text, use_schema),
            "locations": await self.extract_locations(text, use_schema),
            "events": await self.extract_events(text, use_schema),
        }

    async def extract_batch(
        self,
        texts: List[str],
        schema: Type,
        max_concurrency: int = 5
    ) -> BatchExtractionResult:
        """
        Extract entities from multiple texts.

        Args:
            texts: List of input texts
            schema: Schema type to extract
            max_concurrency: Max concurrent extractions

        Returns:
            BatchExtractionResult with all results
        """
        start_time = time.time()
        total_count = len(texts)

        results = []
        successful_count = 0
        failed_count = 0
        total_entities = 0

        for text in texts:
            try:
                entities = await self._extract_all_from_text(text)
                successful_count += 1
                total_entities += len(entities)
                results.append(ExtractionResult(
                    entities=entities,
                    success=True,
                    errors=[]
                ))
            except Exception as e:
                failed_count += 1
                results.append(ExtractionResult(
                    entities=[],
                    success=False,
                    errors=[str(e)]
                ))

        total_time_ms = (time.time() - start_time) * 1000

        return BatchExtractionResult(
            results=results,
            total_texts=total_count,
            successful_count=successful_count,
            failed_count=failed_count,
            total_entities=total_entities,
            total_time_ms=total_time_ms
        )

    async def extract_with_custom_schema(
        self,
        text: str,
        schema: Dict[str, Any]
    ) -> List:
        """
        Extract entities using a custom schema.

        Args:
            text: Input text
            schema: Custom schema definition

        Returns:
            List of extracted entities
        """
        # For now, just use standard NER
        entities = self.ner_model.predict(text)
        return entities

    async def _extract_entities(
        self,
        text: str,
        entity_type: str
    ) -> List[Dict[str, Any]]:
        """
        Internal method to extract specific entity type.

        Args:
            text: Input text
            entity_type: Type of entity to extract

        Returns:
            List of entity dicts
        """
        # Get confidence
        confidence = self.ner_model.get_confidence(text)

        # Hybrid mode: use LLM if confidence is low
        if self.use_hybrid and self.llm_service and confidence < self.config.confidence_threshold:
            # Fallback to LLM
            return await self._llm_fallback(text, entity_type)

        # Use small model
        all_entities = self.ner_model.predict(text)

        # Filter by entity type
        filtered_entities = [
            e for e in all_entities
            if e["label"] == entity_type
        ]

        return filtered_entities

    async def _extract_all_from_text(
        self,
        text: str
    ) -> List[Any]:
        """
        Extract all entities and convert to Pydantic models.

        Args:
            text: Input text

        Returns:
            List of entity objects
        """
        all_entities = []

        # Extract each type
        all_entities.extend(await self.extract_persons(text))
        all_entities.extend(await self.extract_organizations(text))
        all_entities.extend(await self.extract_products(text))
        all_entities.extend(await self.extract_locations(text))
        all_entities.extend(await self.extract_events(text))

        return all_entities

    async def _llm_fallback(
        self,
        text: str,
        entity_type: str
    ) -> List[Dict[str, Any]]:
        """
        Fallback to LLM-based extraction.

        Args:
            text: Input text
            entity_type: Type of entity to extract

        Returns:
            List of entity dicts
        """
        if not self.llm_service:
            return []

        # Call appropriate method based on entity type
        if entity_type == "PERSON":
            entities = await self.llm_service.extract_persons(text)
            return [{"entity": e.name, "label": "PERSON"} for e in entities]
        elif entity_type == "ORG":
            entities = await self.llm_service.extract_organizations(text)
            return [{"entity": e.name, "label": "ORG"} for e in entities]
        elif entity_type == "PRODUCT":
            entities = await self.llm_service.extract_products(text)
            return [{"entity": e.name, "label": "PRODUCT"} for e in entities]
        elif entity_type == "LOCATION":
            entities = await self.llm_service.extract_locations(text)
            return [{"entity": e.name, "label": "LOCATION"} for e in entities]

        return []

    # Synchronous wrappers for compatibility

    def extract_persons_sync(self, text: str) -> List[PersonEntity]:
        """Synchronous wrapper for extract_persons."""
        import asyncio
        return asyncio.run(self.extract_persons(text))

    def extract_organizations_sync(self, text: str) -> List[OrganizationEntity]:
        """Synchronous wrapper for extract_organizations."""
        import asyncio
        return asyncio.run(self.extract_organizations(text))

    def extract_products_sync(self, text: str) -> List[ProductEntity]:
        """Synchronous wrapper for extract_products."""
        import asyncio
        return asyncio.run(self.extract_products(text))

    def extract_locations_sync(self, text: str) -> List[LocationEntity]:
        """Synchronous wrapper for extract_locations."""
        import asyncio
        return asyncio.run(self.extract_locations(text))

    def extract_all_sync(self, text: str) -> Dict[str, List]:
        """Synchronous wrapper for extract_all."""
        import asyncio
        return asyncio.run(self.extract_all(text))
