"""Pydantic-based entity extractor using LangChain."""

import time
from typing import Any, Dict, List, Type, get_type_hints

from langchain.chains import create_extraction_chain_pydantic
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from langchain_entity_extraction.extractors.base_extractor import BaseExtractor
from langchain_entity_extraction.models.extraction_result import ExtractionResult
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class PydanticExtractor(BaseExtractor):
    """
    Entity extractor using Pydantic models.

    Uses LangChain's create_extraction_chain_pydantic which
    provides type-safe extraction with automatic validation.
    This is the recommended approach for production use.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the Pydantic extractor.

        Args:
            llm: LangChain LLM instance
            config: Optional configuration dictionary
        """
        super().__init__(llm, config)
        self.logger.info("Initialized PydanticExtractor")

    async def extract(
        self,
        text: str,
        schema: Type[BaseModel],
        **kwargs
    ) -> ExtractionResult:
        """
        Extract entities from text using Pydantic model.

        Args:
            text: Input text to extract entities from
            schema: Pydantic model class defining entity structure
            **kwargs: Additional parameters (e.g., verbose for debugging)

        Returns:
            ExtractionResult containing extracted entities as Pydantic models

        Example:
            >>> from pydantic import BaseModel, Field
            >>> class Person(BaseModel):
            ...     name: str = Field(..., description="Person's name")
            ...     age: int = Field(..., description="Person's age")
            >>> result = await extractor.extract(
            ...     "John is 30 years old",
            ...     Person
            ... )
        """
        start_time = time.time()
        text_length = len(text)

        try:
            schema_name = schema.__name__ if hasattr(schema, "__name__") else str(schema)
            self.logger.debug(
                f"Starting Pydantic-based extraction",
                schema=schema_name,
                text_length=text_length
            )

            # Create extraction chain with Pydantic schema
            chain = create_extraction_chain_pydantic(
                pydantic_schema=schema,
                llm=self.llm
            )

            # Run extraction
            verbose = kwargs.get("verbose", False)
            result = await chain.ainvoke(
                {"input": [text]},
                {"verbose": verbose}
            )

            # Extract entities from result
            entities = self._parse_result(result)

            extraction_time_ms = self._measure_time(start_time)

            self.logger.info(
                f"Pydantic-based extraction completed",
                schema=schema_name,
                entity_count=len(entities),
                time_ms=extraction_time_ms
            )

            return self._create_result(
                entities=entities,
                schema_type=schema_name,
                text_length=text_length,
                extraction_time_ms=extraction_time_ms,
                raw_output=result if self.config.get("include_raw_output") else None
            )

        except Exception as e:
            self.logger.error(f"Pydantic extraction failed: {str(e)}")
            return self.handle_error(
                e,
                {
                    "text_length": text_length,
                    "schema": str(schema)
                }
            )

    def _parse_result(self, result: Dict[str, Any]) -> List[BaseModel]:
        """
        Parse the extraction chain result.

        Args:
            result: Raw result from extraction chain

        Returns:
            List of extracted entities as Pydantic model instances
        """
        # LangChain extraction chain returns data in different formats
        # depending on the version. Handle common cases.

        if isinstance(result, dict):
            # Case 1: {'data': [...]}
            if "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    return data
                return [data]

            # Case 2: {'text': ..., '...': ...}
            # Look for list values
            for key, value in result.items():
                if isinstance(value, list) and len(value) > 0:
                    # Verify they are Pydantic models
                    if isinstance(value[0], BaseModel):
                        return value

        # Case 3: Direct list
        if isinstance(result, list):
            return result

        # Fallback: empty list
        self.logger.warning(f"Unexpected result format: {type(result)}")
        return []

    async def extract_multiple(
        self,
        text: str,
        schemas: List[Type[BaseModel]],
        **kwargs
    ) -> Dict[str, List[BaseModel]]:
        """
        Extract multiple entity types from text.

        Args:
            text: Input text to extract entities from
            schemas: List of Pydantic model classes
            **kwargs: Additional parameters

        Returns:
            Dictionary mapping schema names to extracted entities
        """
        results = {}

        for schema in schemas:
            schema_name = schema.__name__
            result = await self.extract(text, schema, **kwargs)
            results[schema_name] = result.entities

        return results
