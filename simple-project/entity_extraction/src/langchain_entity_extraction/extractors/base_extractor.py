"""Base extractor interface for entity extraction."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from langchain_entity_extraction.models.extraction_result import (
    ExtractionResult,
    ExtractionError,
)
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class BaseExtractor(ABC):
    """
    Base class for entity extractors.

    Provides common functionality for all extractors including
    error handling, logging, and result processing.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the base extractor.

        Args:
            llm: LangChain LLM instance
            config: Optional configuration dictionary
        """
        self.llm = llm
        self.config = config or {}
        self.logger = logger.bind(extractor=self.__class__.__name__)

    @abstractmethod
    async def extract(
        self,
        text: str,
        schema: Any,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract entities from text.

        Args:
            text: Input text to extract entities from
            schema: Schema definition (dict or Pydantic model)
            **kwargs: Additional parameters

        Returns:
            ExtractionResult containing extracted entities
        """
        pass

    def _create_result(
        self,
        entities: List[Any],
        schema_type: Optional[str] = None,
        text_length: int = 0,
        extraction_time_ms: Optional[float] = None,
        raw_output: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Create an ExtractionResult.

        Args:
            entities: List of extracted entities
            schema_type: Type of schema used
            text_length: Length of input text
            extraction_time_ms: Time taken for extraction
            raw_output: Raw LLM output

        Returns:
            ExtractionResult instance
        """
        return ExtractionResult(
            entities=entities,
            schema_type=schema_type,
            success=True,
            text_length=text_length,
            extraction_time_ms=extraction_time_ms,
            raw_output=raw_output
        )

    def _create_error_result(
        self,
        message: str,
        error_type: str,
        retry_count: int = 0,
        text_length: int = 0
    ) -> ExtractionResult:
        """
        Create an ExtractionResult with error.

        Args:
            message: Error message
            error_type: Type of error
            retry_count: Number of retries attempted
            text_length: Length of input text

        Returns:
            ExtractionResult with error
        """
        return ExtractionResult(
            entities=[],
            success=False,
            errors=[
                ExtractionError(
                    message=message,
                    error_type=error_type,
                    retry_count=retry_count
                )
            ],
            text_length=text_length
        )

    def _measure_time(self, start_time: float) -> float:
        """
        Measure elapsed time in milliseconds.

        Args:
            start_time: Start time from time.time()

        Returns:
            Elapsed time in milliseconds
        """
        return (time.time() - start_time) * 1000

    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> ExtractionResult:
        """
        Handle extraction error.

        Args:
            error: The exception that occurred
            context: Context information about the error

        Returns:
            ExtractionResult with error information
        """
        error_type = type(error).__name__
        error_message = str(error)

        self.logger.error(
            f"Extraction error: {error_type}: {error_message}",
            **context
        )

        return self._create_error_result(
            message=error_message,
            error_type=error_type,
            text_length=context.get("text_length", 0)
        )

    def validate_result(self, result: Any, schema: Any) -> bool:
        """
        Validate extraction result against schema.

        Args:
            result: Extraction result to validate
            schema: Expected schema

        Returns:
            True if valid, False otherwise
        """
        if result is None:
            return False

        if isinstance(result, list):
            return len(result) > 0

        return True
