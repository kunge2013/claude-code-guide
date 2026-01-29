"""Schema-based entity extractor using LangChain."""

import time
from typing import Any, Dict, List

from langchain.chains import create_extraction_chain
from langchain_core.language_models.chat_models import BaseChatModel

from langchain_entity_extraction.extractors.base_extractor import BaseExtractor
from langchain_entity_extraction.models.extraction_result import ExtractionResult
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaExtractor(BaseExtractor):
    """
    Entity extractor using dictionary-based schema.

    Uses LangChain's create_extraction_chain with a dictionary
    schema definition. This is the more flexible approach that
    works with various LLM providers.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the schema extractor.

        Args:
            llm: LangChain LLM instance
            config: Optional configuration dictionary
        """
        super().__init__(llm, config)
        self.logger.info("Initialized SchemaExtractor")

    async def extract(
        self,
        text: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> ExtractionResult:
        """
        Extract entities from text using schema-based extraction.

        Args:
            text: Input text to extract entities from
            schema: Dictionary schema defining entity structure
            **kwargs: Additional parameters (e.g., verbose for debugging)

        Returns:
            ExtractionResult containing extracted entities

        Example:
            >>> schema = {
            ...     "properties": {
            ...         "name": {"type": "string"},
            ...         "age": {"type": "integer"}
            ...     },
            ...     "required": ["name"]
            ... }
            >>> result = await extractor.extract(
            ...     "John is 30 years old",
            ...     schema
            ... )
        """
        start_time = time.time()
        text_length = len(text)

        try:
            self.logger.debug(
                f"Starting schema-based extraction",
                text_length=text_length,
                schema_keys=list(schema.get("properties", {}).keys())
            )

            # Create extraction chain
            chain = create_extraction_chain(schema, self.llm)

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
                f"Schema-based extraction completed",
                entity_count=len(entities),
                time_ms=extraction_time_ms
            )

            return self._create_result(
                entities=entities,
                schema_type="dict_schema",
                text_length=text_length,
                extraction_time_ms=extraction_time_ms,
                raw_output=result if self.config.get("include_raw_output") else None
            )

        except Exception as e:
            self.logger.error(f"Schema extraction failed: {str(e)}")
            return self.handle_error(
                e,
                {
                    "text_length": text_length,
                    "schema": schema
                }
            )

    def _parse_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse the extraction chain result.

        Args:
            result: Raw result from extraction chain

        Returns:
            List of extracted entities as dictionaries
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
                    # Check if it looks like entities (dict with string keys)
                    if isinstance(value[0], dict):
                        return value

        # Case 3: Direct list
        if isinstance(result, list):
            return result

        # Fallback: empty list
        self.logger.warning(f"Unexpected result format: {type(result)}")
        return []
