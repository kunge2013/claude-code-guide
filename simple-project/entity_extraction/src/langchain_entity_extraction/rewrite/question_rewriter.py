"""Question rewriting service using LangChain."""

import json
import time
from datetime import date
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from langchain_entity_extraction.llm.langchain_llm import create_langchain_llm
from langchain_entity_extraction.models.rewrite_models import (
    OriginalQuestion,
    RewrittenQuestion,
    RewriteResult,
    BatchRewriteResult,
)
from langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
from langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
from langchain_entity_extraction.rewrite.prompts import (
    get_system_prompt,
    get_user_prompt,
    get_simple_prompt,
)
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class QuestionRewriter:
    """
    Question rewriting service using LangChain and LLM.

    Rewrites natural language questions to be more structured and explicit,
    making them easier for downstream entity extraction and SQL generation.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize the question rewriter.

        Args:
            llm: LangChain LLM instance (created from config if not provided)
            max_retries: Maximum number of retries for failed rewrites
            timeout: Timeout in seconds for each rewrite attempt
        """
        self.llm = llm or create_langchain_llm()
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize utilities
        self.time_normalizer = TimeNormalizer()
        self.entity_mapper = EntityMapper()

        logger.info(
            "QuestionRewriter initialized",
            llm_type=type(self.llm).__name__,
            max_retries=max_retries,
            timeout=timeout
        )

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
            context: Optional context information (previous questions, etc.)
            use_simple_prompt: Whether to use simplified prompt

        Returns:
            RewriteResult containing the rewritten question

        Examples:
            >>> rewriter = QuestionRewriter()
            >>> result = await rewriter.rewrite("今年cdn产品金额是多少")
            >>> assert result.success
            >>> print(result.rewritten.rewritten)
            "产品ID为cdn，时间为2026年的出账金额是多少"
        """
        start_time = time.time()

        # Create original question model
        original = OriginalQuestion(content=question)
        if context:
            original.metadata.update(context)

        try:
            logger.info(f"Rewriting question: {question}")

            # Prepare prompt
            date_info = self.time_normalizer.get_current_date_info()

            if use_simple_prompt:
                prompt = get_simple_prompt(
                    question,
                    date_info["date"]
                )
                messages = [
                    SystemMessage(content=get_system_prompt()),
                    HumanMessage(content=prompt)
                ]
            else:
                prompt = get_user_prompt(
                    question,
                    date_info["date"],
                    date_info["year"],
                    date_info["month"],
                    ", ".join(self.entity_mapper.get_all_products()),
                    ", ".join(self.entity_mapper.get_all_fields())
                )
                messages = [
                    SystemMessage(content=get_system_prompt()),
                    HumanMessage(content=prompt)
                ]

            # Invoke LLM with retry logic
            response = await self._invoke_with_retry(messages)

            # Parse response
            rewritten = self._parse_response(response, question)

            processing_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Question rewritten successfully",
                original=question,
                rewritten=rewritten.rewritten,
                time_ms=processing_time_ms
            )

            return RewriteResult(
                success=True,
                original=original,
                rewritten=rewritten,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Failed to rewrite question: {str(e)}"

            logger.error(error_msg, exc_info=True)

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

        logger.info(
            f"Starting batch rewrite",
            total_count=total_count,
            max_concurrency=max_concurrency
        )

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

        logger.info(
            f"Batch rewrite completed",
            successful=successful_count,
            failed=failed_count,
            total_time_ms=total_time_ms
        )

        return BatchRewriteResult(
            results=rewrite_results,
            total_count=total_count,
            successful_count=successful_count,
            failed_count=failed_count,
            total_time_ms=total_time_ms
        )

    async def _invoke_with_retry(self, messages: List) -> str:
        """
        Invoke LLM with retry logic.

        Args:
            messages: Messages to send to LLM

        Returns:
            LLM response string

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = await self.llm.ainvoke(messages)
                return response.content
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"LLM invocation failed (attempt {attempt + 1}/{self.max_retries})",
                    error=str(e)
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

        raise last_exception

    def _parse_response(self, response: str, original_question: str) -> RewrittenQuestion:
        """
        Parse LLM response into RewrittenQuestion model.

        Args:
            response: LLM response string
            original_question: Original question content

        Returns:
            RewrittenQuestion model

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to parse as JSON
            # Handle markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code block markers
                response = "\n".join(response.split("\n")[1:-1])

            data = json.loads(response)

            # Extract fields with defaults
            rewritten = data.get("rewritten", original_question)
            entities = data.get("entities", {})
            reasoning = data.get("reasoning", "")
            changes_made = data.get("changes_made", [])

            return RewrittenQuestion(
                original=original_question,
                rewritten=rewritten,
                entities=entities,
                reasoning=reasoning,
                changes_made=changes_made
            )

        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract information manually
            logger.warning(f"Failed to parse JSON response, attempting manual extraction")

            # Try to find the rewritten question in the response
            rewritten = original_question
            if "改写后问题" in response or "rewritten" in response.lower():
                lines = response.split("\n")
                for line in lines:
                    if "改写后问题" in line or "rewritten" in line.lower():
                        # Extract content after the colon
                        if ":" in line or "：" in line:
                            rewritten = line.split(":")[-1].split("：")[-1].strip().strip('"')
                            break

            return RewrittenQuestion(
                original=original_question,
                rewritten=rewritten,
                entities={},
                reasoning="无法解析JSON，使用默认值"
            )
        except Exception as e:
            logger.error(f"Failed to parse response: {str(e)}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

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
