"""
Hybrid Service - Combines Small Model and LLM.

Provides intelligent routing between small model and LLM
based on confidence scores and query complexity.
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
    LocationEntity,
)
from langchain_entity_extraction.models.rewrite_models import (
    RewriteResult,
    BatchRewriteResult,
)
from langchain_entity_extraction.small_model.services.small_extraction_service import SmallExtractionService
from langchain_entity_extraction.small_model.services.small_rewrite_service import SmallRewriteService
from langchain_entity_extraction.small_model.config.ner_config import NERConfig
from langchain_entity_extraction.small_model.config.t5_config import T5Config


@dataclass
class HybridStats:
    """Statistics for hybrid service routing."""
    small_model_count: int = 0
    llm_count: int = 0
    small_model_avg_time_ms: float = 0.0
    llm_avg_time_ms: float = 0.0

    def total_count(self) -> int:
        return self.small_model_count + self.llm_count

    def small_model_ratio(self) -> float:
        total = self.total_count()
        if total == 0:
            return 0.0
        return self.small_model_count / total


class HybridService:
    """
    Hybrid service combining small model and LLM.

    Uses intelligent routing to choose between small model (fast, cheap)
    and LLM (accurate, expensive) based on confidence scores.

    Routing Strategy:
    - Confidence >= 0.9: Use small model only
    - 0.7 <= Confidence < 0.9: Use small model + verify with LLM
    - Confidence < 0.7: Use LLM only

    Example:
        >>> service = HybridService()
        >>> # Most queries will use small model
        >>> result = await service.rewrite("今年cdn产品金额是多少")
        >>> # Complex queries may use LLM
        >>> result = await service.rewrite("复杂的模糊查询...")
    """

    def __init__(
        self,
        ner_model_path: str = "models/ner_bert",
        t5_model_path: str = "models/rewrite_t5",
        ner_config: Optional[NERConfig] = None,
        t5_config: Optional[T5Config] = None,
        confidence_threshold: float = 0.7,
        verify_threshold: float = 0.9
    ):
        """
        Initialize the hybrid service.

        Args:
            ner_model_path: Path to NER model
            t5_model_path: Path to T5 model
            ner_config: NER configuration
            t5_config: T5 configuration
            confidence_threshold: Below this, use LLM only
            verify_threshold: Above this, use small model only
        """
        self.confidence_threshold = confidence_threshold
        self.verify_threshold = verify_threshold

        # Initialize small model services
        self.small_extraction = SmallExtractionService(
            model_path=ner_model_path,
            config=ner_config,
            use_hybrid=False
        )
        self.small_rewrite = SmallRewriteService(
            model_path=t5_model_path,
            ner_model_path=ner_model_path,
            config=t5_config,
            ner_config=ner_config,
            use_hybrid=False
        )

        # Initialize LLM services (lazy load)
        self.llm_extraction = None
        self.llm_rewrite = None

        # Statistics
        self.extraction_stats = HybridStats()
        self.rewrite_stats = HybridStats()

    # ===== Entity Extraction Methods =====

    async def extract_persons(self, text: str) -> List[PersonEntity]:
        """
        Extract person entities using hybrid routing.

        Args:
            text: Input text

        Returns:
            List of PersonEntity objects
        """
        confidence = self.small_extraction.ner_model.get_confidence(text)

        if confidence >= self.verify_threshold:
            # Use small model only
            self.extraction_stats.small_model_count += 1
            return await self.small_extraction.extract_persons(text)
        elif confidence >= self.confidence_threshold:
            # Use small model + verify
            self.extraction_stats.small_model_count += 1
            entities = await self.small_extraction.extract_persons(text)
            if not self._should_verify_with_llm(entities, text):
                return entities
            # Fall through to LLM verification
        else:
            # Use LLM only
            self.extraction_stats.llm_count += 1
            return await self._llm_extract_persons(text)

        # LLM verification
        llm_entities = await self._llm_extract_persons(text)
        return self._merge_extraction_results(entities, llm_entities)

    async def extract_organizations(self, text: str) -> List[OrganizationEntity]:
        """Extract organization entities using hybrid routing."""
        confidence = self.small_extraction.ner_model.get_confidence(text)

        if confidence >= self.verify_threshold:
            self.extraction_stats.small_model_count += 1
            return await self.small_extraction.extract_organizations(text)
        elif confidence >= self.confidence_threshold:
            self.extraction_stats.small_model_count += 1
            entities = await self.small_extraction.extract_organizations(text)
            if not self._should_verify_with_llm(entities, text):
                return entities
        else:
            self.extraction_stats.llm_count += 1
            return await self._llm_extract_organizations(text)

        llm_entities = await self._llm_extract_organizations(text)
        return self._merge_extraction_results(entities, llm_entities)

    async def extract_products(self, text: str) -> List[ProductEntity]:
        """Extract product entities using hybrid routing."""
        confidence = self.small_extraction.ner_model.get_confidence(text)

        if confidence >= self.verify_threshold:
            self.extraction_stats.small_model_count += 1
            return await self.small_extraction.extract_products(text)
        elif confidence >= self.confidence_threshold:
            self.extraction_stats.small_model_count += 1
            entities = await self.small_extraction.extract_products(text)
            if not self._should_verify_with_llm(entities, text):
                return entities
        else:
            self.extraction_stats.llm_count += 1
            return await self._llm_extract_products(text)

        llm_entities = await self._llm_extract_products(text)
        return self._merge_extraction_results(entities, llm_entities)

    async def extract_all(self, text: str) -> Dict[str, List]:
        """Extract all entity types using hybrid routing."""
        return {
            "persons": await self.extract_persons(text),
            "organizations": await self.extract_organizations(text),
            "products": await self.extract_products(text),
            "locations": await self.extract_locations(text),
            "events": await self.small_extraction.extract_events(text),
        }

    async def extract_locations(self, text: str) -> List[LocationEntity]:
        """Extract location entities using hybrid routing."""
        confidence = self.small_extraction.ner_model.get_confidence(text)

        if confidence >= self.verify_threshold:
            self.extraction_stats.small_model_count += 1
            return await self.small_extraction.extract_locations(text)
        elif confidence >= self.confidence_threshold:
            self.extraction_stats.small_model_count += 1
            entities = await self.small_extraction.extract_locations(text)
            if not self._should_verify_with_llm(entities, text):
                return entities
        else:
            self.extraction_stats.llm_count += 1
            return await self._llm_extract_locations(text)

        llm_entities = await self._llm_extract_locations(text)
        return self._merge_extraction_results(entities, llm_entities)

    # ===== Question Rewrite Methods =====

    async def rewrite(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        use_simple_prompt: bool = False
    ) -> RewriteResult:
        """
        Rewrite question using hybrid routing.

        Args:
            question: Original question
            context: Optional context
            use_simple_prompt: Whether to use simple prompt

        Returns:
            RewriteResult with rewritten question
        """
        confidence = self.small_rewrite.rewrite_model.get_confidence(question)

        start_time = time.time()

        if confidence >= self.verify_threshold:
            # Use small model only
            self.rewrite_stats.small_model_count += 1
            result = await self.small_rewrite.rewrite(question, context, use_simple_prompt)
            self.rewrite_stats.small_model_avg_time_ms = (
                self._update_avg(
                    self.rewrite_stats.small_model_avg_time_ms,
                    self.rewrite_stats.small_model_count,
                    result.processing_time_ms
                )
            )
            return result
        elif confidence >= self.confidence_threshold:
            # Use small model + verify
            self.rewrite_stats.small_model_count += 1
            result = await self.small_rewrite.rewrite(question, context, use_simple_prompt)
            if not self._should_verify_rewrite_with_llm(result, question):
                self.rewrite_stats.small_model_avg_time_ms = (
                    self._update_avg(
                        self.rewrite_stats.small_model_avg_time_ms,
                        self.rewrite_stats.small_model_count,
                        result.processing_time_ms
                    )
                )
                return result
            # Fall through to LLM
        else:
            # Use LLM only
            self.rewrite_stats.llm_count += 1
            return await self._llm_rewrite(question, context, use_simple_prompt)

        # LLM verification/fallback
        llm_result = await self._llm_rewrite(question, context, use_simple_prompt)
        self.rewrite_stats.llm_avg_time_ms = (
            self._update_avg(
                self.rewrite_stats.llm_avg_time_ms,
                self.rewrite_stats.llm_count,
                llm_result.processing_time_ms
            )
        )
        return llm_result

    async def rewrite_batch(
        self,
        questions: List[str],
        max_concurrency: int = 5,
        use_simple_prompt: bool = False
    ) -> BatchRewriteResult:
        """Rewrite multiple questions using hybrid routing."""
        import asyncio

        start_time = time.time()

        # Use small model batch for efficiency
        small_results = await self.small_rewrite.rewrite_batch(
            questions,
            max_concurrency,
            use_simple_prompt
        )

        # Check which ones need LLM verification
        verified_results = []
        successful_count = 0
        failed_count = 0

        for i, result in enumerate(small_results.results):
            if result.success:
                confidence = self.small_rewrite.rewrite_model.get_confidence(questions[i])
                if confidence >= self.verify_threshold:
                    verified_results.append(result)
                    successful_count += 1
                elif confidence >= self.confidence_threshold:
                    # Verify with LLM (one by one)
                    llm_result = await self._llm_rewrite(questions[i])
                    verified_results.append(llm_result)
                    if llm_result.success:
                        successful_count += 1
                    else:
                        failed_count += 1
                else:
                    # Use LLM
                    llm_result = await self._llm_rewrite(questions[i])
                    verified_results.append(llm_result)
                    if llm_result.success:
                        successful_count += 1
                    else:
                        failed_count += 1
            else:
                verified_results.append(result)
                failed_count += 1

        total_time_ms = (time.time() - start_time) * 1000

        return BatchRewriteResult(
            results=verified_results,
            total_count=len(questions),
            successful_count=successful_count,
            failed_count=failed_count,
            total_time_ms=total_time_ms
        )

    # ===== Helper Methods =====

    def _should_verify_with_llm(self, entities: List, text: str) -> bool:
        """Determine if results need LLM verification."""
        # Verify if no entities found but text seems to have entities
        if not entities and len(text) > 10:
            return True
        # Verify if very few entities found
        if len(entities) < 2 and len(text) > 20:
            return True
        return False

    def _should_verify_rewrite_with_llm(self, result: RewriteResult, question: str) -> bool:
        """Determine if rewrite needs LLM verification."""
        # Verify if no entities extracted
        if result.rewritten and not result.rewritten.entities:
            return True
        # Verify if question is complex (long, contains multiple clauses)
        if len(question) > 50 or question.count("和") > 1:
            return True
        return False

    def _merge_extraction_results(
        self,
        small_results: List,
        llm_results: List
    ) -> List:
        """Merge results from small model and LLM."""
        # Prefer LLM results when available
        if llm_results:
            return llm_results
        return small_results

    def _update_avg(
        self,
        current_avg: float,
        count: int,
        new_value: float
    ) -> float:
        """Update running average."""
        if count == 1:
            return new_value
        return (current_avg * (count - 1) + new_value) / count

    # ===== LLM Fallback Methods =====

    async def _llm_extract_persons(self, text: str) -> List[PersonEntity]:
        """Fallback to LLM for person extraction."""
        if not self.llm_extraction:
            self._init_llm_extraction()
        if self.llm_extraction:
            return await self.llm_extraction.extract_persons(text)
        return []

    async def _llm_extract_organizations(self, text: str) -> List[OrganizationEntity]:
        """Fallback to LLM for organization extraction."""
        if not self.llm_extraction:
            self._init_llm_extraction()
        if self.llm_extraction:
            return await self.llm_extraction.extract_organizations(text)
        return []

    async def _llm_extract_products(self, text: str) -> List[ProductEntity]:
        """Fallback to LLM for product extraction."""
        if not self.llm_extraction:
            self._init_llm_extraction()
        if self.llm_extraction:
            return await self.llm_extraction.extract_products(text)
        return []

    async def _llm_extract_locations(self, text: str) -> List[LocationEntity]:
        """Fallback to LLM for location extraction."""
        if not self.llm_extraction:
            self._init_llm_extraction()
        if self.llm_extraction:
            return await self.llm_extraction.extract_locations(text)
        return []

    async def _llm_rewrite(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        use_simple_prompt: bool = False
    ) -> RewriteResult:
        """Fallback to LLM for question rewriting."""
        if not self.llm_rewrite:
            self._init_llm_rewrite()
        if self.llm_rewrite:
            return await self.llm_rewrite.rewrite(question, context, use_simple_prompt)
        # Fallback to small model result
        return await self.small_rewrite.rewrite(question, context, use_simple_prompt)

    def _init_llm_extraction(self):
        """Initialize LLM extraction service."""
        try:
            from langchain_entity_extraction.services.extraction_service import ExtractionService
            self.llm_extraction = ExtractionService()
        except ImportError:
            self.llm_extraction = None

    def _init_llm_rewrite(self):
        """Initialize LLM rewrite service."""
        try:
            from langchain_entity_extraction.rewrite.question_rewriter import QuestionRewriter
            self.llm_rewrite = QuestionRewriter()
        except ImportError:
            self.llm_rewrite = None

    # ===== Statistics Methods =====

    def get_stats(self) -> Dict[str, Any]:
        """Get hybrid service statistics."""
        return {
            "extraction": {
                "small_model_count": self.extraction_stats.small_model_count,
                "llm_count": self.extraction_stats.llm_count,
                "small_model_ratio": self.extraction_stats.small_model_ratio(),
                "total_count": self.extraction_stats.total_count(),
            },
            "rewrite": {
                "small_model_count": self.rewrite_stats.small_model_count,
                "llm_count": self.rewrite_stats.llm_count,
                "small_model_ratio": self.rewrite_stats.small_model_ratio(),
                "total_count": self.rewrite_stats.total_count(),
            },
        }

    def reset_stats(self):
        """Reset statistics."""
        self.extraction_stats = HybridStats()
        self.rewrite_stats = HybridStats()
