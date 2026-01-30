"""
Small Model Question Rewrite Service.

Provides question rewriting using T5-based Seq2Seq model.
Interface compatible with existing QuestionRewriter.
"""

import json
import time
from typing import List, Dict, Any, Optional

from langchain_entity_extraction.models.rewrite_models import (
    OriginalQuestion,
    RewrittenQuestion,
    RewriteResult,
    BatchRewriteResult,
)
from langchain_entity_extraction.small_model.models.seq2seq_model import QuestionRewriteModel
from langchain_entity_extraction.small_model.models.ner_model import EntityRecognitionModel
from langchain_entity_extraction.small_model.utils.rule_normalizer import RuleNormalizer
from langchain_entity_extraction.small_model.config.t5_config import T5Config
from langchain_entity_extraction.small_model.config.ner_config import NERConfig


class SmallRewriteService:
    """
    Small model question rewrite service.

    Uses T5-based Seq2Seq model for fast, local question rewriting.
    Interface compatible with existing QuestionRewriter.

    Example:
        >>> service = SmallRewriteService()
        >>> result = await service.rewrite("今年cdn产品金额是多少")
        >>> print(result.rewritten.rewritten)
        "产品ID为cdn，时间为2026年的出账金额是多少"
    """

    def __init__(
        self,
        model_path: str = "models/rewrite_t5",
        ner_model_path: str = "models/ner_bert",
        config: Optional[T5Config] = None,
        ner_config: Optional[NERConfig] = None,
        use_hybrid: bool = False
    ):
        """
        Initialize the rewrite service.

        Args:
            model_path: Path to trained T5 model
            ner_model_path: Path to trained NER model (for entity extraction)
            config: T5 configuration (optional)
            ner_config: NER configuration (optional)
            use_hybrid: Whether to use hybrid mode (small model + LLM fallback)
        """
        self.t5_config = config or T5Config()
        self.ner_config = ner_config or NERConfig()
        self.use_hybrid = use_hybrid

        # Initialize T5 model
        self.rewrite_model = QuestionRewriteModel(model_path, self.t5_config)

        # Initialize NER model (for entity extraction)
        self.ner_model = EntityRecognitionModel(ner_model_path, self.ner_config)

        # Initialize normalizer
        self.normalizer = RuleNormalizer()

        # Hybrid mode: initialize LLM fallback
        self.llm_service = None
        if use_hybrid:
            try:
                from langchain_entity_extraction.rewrite.question_rewriter import QuestionRewriter
                self.llm_service = QuestionRewriter()
            except ImportError:
                self.use_hybrid = False

    async def rewrite(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        use_simple_prompt: bool = False
    ) -> RewriteResult:
        """
        Rewrite a single question.

        Args:
            question: The original question to rewrite
            context: Optional context information
            use_simple_prompt: Whether to use simplified prompt (ignored for T5)

        Returns:
            RewriteResult containing the rewritten question

        Example:
            >>> service = SmallRewriteService()
            >>> result = await service.rewrite("今年cdn产品金额是多少")
            >>> assert result.success
            >>> print(result.rewritten.rewritten)
        """
        start_time = time.time()

        # Create original question model
        original = OriginalQuestion(content=question)
        if context:
            original.metadata.update(context)

        try:
            # Extract entities using NER
            raw_entities = self.ner_model.predict(question)

            # Normalize entities
            normalized_entities = self.normalizer.normalize_entities(raw_entities)

            # Rewrite using T5
            rewritten_text = self.rewrite_model.rewrite(
                question,
                entities=normalized_entities
            )

            # Get confidence
            confidence = self.rewrite_model.get_confidence(question)

            # Build rewritten question
            rewritten = RewrittenQuestion(
                original=question,
                rewritten=rewritten_text,
                entities=normalized_entities,
                confidence=confidence,
                reasoning="T5-based seq2seq generation",
                changes_made=self._detect_changes(question, rewritten_text)
            )

            processing_time_ms = (time.time() - start_time) * 1000

            return RewriteResult(
                success=True,
                original=original,
                rewritten=rewritten,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Failed to rewrite question: {str(e)}"

            return RewriteResult(
                success=False,
                original=original,
                errors=[error_msg],
                processing_time_ms=processing_time_ms
            )

    async def rewrite_batch(
        self,
        questions: List[str],
        max_concurrency: int = 5,
        use_simple_prompt: bool = False
    ) -> BatchRewriteResult:
        """
        Rewrite multiple questions in batch.

        Args:
            questions: List of questions to rewrite
            max_concurrency: Maximum number of concurrent rewrites
            use_simple_prompt: Whether to use simplified prompt

        Returns:
            BatchRewriteResult containing all rewrite results
        """
        import asyncio

        start_time = time.time()
        total_count = len(questions)

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)

        async def rewrite_with_limit(question: str) -> RewriteResult:
            async with semaphore:
                return await self.rewrite(question, use_simple_prompt=use_simple_prompt)

        # Run rewrites with concurrency limit
        results = await asyncio.gather(
            *[rewrite_with_limit(q) for q in questions],
            return_exceptions=True
        )

        # Process results
        rewrite_results = []
        successful_count = 0
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                rewrite_results.append(
                    RewriteResult(
                        success=False,
                        original=OriginalQuestion(content=questions[i]),
                        errors=[str(result)]
                    )
                )
            elif result.success:
                successful_count += 1
                rewrite_results.append(result)
            else:
                failed_count += 1
                rewrite_results.append(result)

        total_time_ms = (time.time() - start_time) * 1000

        return BatchRewriteResult(
            results=rewrite_results,
            total_count=total_count,
            successful_count=successful_count,
            failed_count=failed_count,
            total_time_ms=total_time_ms
        )

    def _detect_changes(
        self,
        original: str,
        rewritten: str
    ) -> List[str]:
        """
        Detect changes made during rewriting.

        Args:
            original: Original question
            rewritten: Rewritten question

        Returns:
            List of change descriptions
        """
        changes = []

        # Check for time normalization
        if "今年" in original and "2026" in rewritten:
            changes.append("时间规范化：今年 → 2026年")
        elif "去年" in original and "2025" in rewritten:
            changes.append("时间规范化：去年 → 2025年")

        # Check for product ID format
        if "产品ID为" in rewritten and "产品ID为" not in original:
            changes.append("产品ID规范化")

        # Check for field normalization
        if "出账金额" in rewritten and "金额" in original:
            changes.append("字段规范化：金额 → 出账金额")

        # Check for structural changes
        if "时间为" in rewritten and "时间为" not in original:
            changes.append("添加时间结构化信息")

        if len(changes) == 0 and original != rewritten:
            changes.append("语句重组")

        return changes

    # Synchronous wrapper for compatibility

    def rewrite_sync(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        use_simple_prompt: bool = False
    ) -> RewriteResult:
        """
        Synchronous wrapper for rewrite method.

        Args:
            question: The original question to rewrite
            context: Optional context information
            use_simple_prompt: Whether to use simplified prompt

        Returns:
            RewriteResult containing the rewritten question
        """
        import asyncio
        return asyncio.run(
            self.rewrite(question, context, use_simple_prompt)
        )

    def rewrite_batch_sync(
        self,
        questions: List[str],
        max_concurrency: int = 5,
        use_simple_prompt: bool = False
    ) -> BatchRewriteResult:
        """
        Synchronous wrapper for rewrite_batch method.

        Args:
            questions: List of questions to rewrite
            max_concurrency: Maximum number of concurrent rewrites
            use_simple_prompt: Whether to use simplified prompt

        Returns:
            BatchRewriteResult containing all rewrite results
        """
        import asyncio
        return asyncio.run(
            self.rewrite_batch(questions, max_concurrency, use_simple_prompt)
        )
