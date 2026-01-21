"""
Intent Classification Agent

Classifies user's question intent to route the request appropriately:
- 'query': Data query requiring database access
- 'greeting': Greeting/casual conversation
- 'help': Help/documentation request
- 'clarification': Needs more information

This helps optimize the pipeline by skipping expensive operations for non-query intents.
"""

import json
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase
from langchain_chatbi.models.response_models import (
    IntentClassification,
    AmbiguityDetection,
)


class IntentClassificationAgent(LangChainAgentBase):
    """
    Agent for classifying user question intent and detecting ambiguity.

    Uses LangChain with structured output to reliably classify intents and
    detect when questions are too ambiguous to answer.
    """

    # Intent classification system prompt
    INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Business Intelligence (BI) system.

Your job is to classify the user's question into one of these intents:

1. **query**: The user is asking for data, metrics, or analysis. This requires database access.
   - Examples: "What are the top 5 products by sales?", "Show me revenue trends", "How many customers do we have?"

2. **greeting**: The user is greeting or engaging in casual conversation.
   - Examples: "Hello", "Hi there", "Good morning"

3. **help**: The user is asking for help or documentation.
   - Examples: "How do I use this?", "What can you do?", "Help me"

4. **clarification**: The user's question is critically ambiguous and cannot be answered without more information.
   - This should be RARE - only use when the question is impossibly vague like "show me data" with no context.

5. **unknown**: The intent is unclear and doesn't fit other categories.

Classify based on the primary intent of the question."""

    # Ambiguity detection system prompt
    AMBIGUITY_SYSTEM_PROMPT = """You are an ambiguity detector for a BI system.

Your job is to analyze if a user's question is CRITICALLY ambiguous - meaning it cannot be answered without more information.

IMPORTANT GUIDELINES:
- ONLY mark as ambiguous if the question has NO clear subject or intent
- Questions like "top 5 products by sales" are CLEAR even without knowing the database schema
- Questions like "show me something" or "give me data" are AMBIGUOUS
- If a reasonable person would understand what the user wants, it's NOT ambiguous
- Prefer returning NOT ambiguous unless absolutely certain

Ambiguity types:
- **completely_vague**: No subject at all (e.g., "show me data")
- **multiple_interpretations**: Could mean several different things
- **missing_critical_context**: Missing a key parameter like date range
- **none**: Not ambiguous (use this for 99% of business queries)"""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the IntentClassificationAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="IntentClassificationAgent", llm=llm, callbacks=callbacks)

        # Create intent classification prompt with format instructions
        self._intent_prompt = ChatPromptTemplate.from_messages([
            ("system", self.INTENT_SYSTEM_PROMPT),
            ("human", "Question: {question}\n\nContext: {context}\n\n{format_instructions}")
        ])

        # Create ambiguity detection prompt with format instructions
        self._ambiguity_prompt = ChatPromptTemplate.from_messages([
            ("system", self.AMBIGUITY_SYSTEM_PROMPT),
            ("human", "Question: {question}\n\n{format_instructions}")
        ])

        # Create parsers
        self._intent_parser = PydanticOutputParser(pydantic_object=IntentClassification)
        self._ambiguity_parser = PydanticOutputParser(pydantic_object=AmbiguityDetection)

    def classify_sync(
        self,
        question: str,
        context: Optional[str] = None
    ) -> IntentClassification:
        """
        Classify the user's intent (synchronous version).

        Args:
            question: The user's question
            context: Optional conversation context

        Returns:
            IntentClassification result
        """
        logger.debug(f"[{self.name}]: Classifying intent for '{question}'")

        context = context or "No previous context"

        try:
            messages = self._intent_prompt.format_messages(
                question=question,
                context=context,
                format_instructions=self._intent_parser.get_format_instructions()
            )

            # Use synchronous invoke
            response = self._invoke(messages)

            # Parse the response
            result = self._intent_parser.parse(response.content)

            logger.info(
                f"[{self.name}]: Classified as '{result.intent}' "
                f"(confidence: {result.confidence})"
            )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Intent classification failed: {e}")
            # Return unknown intent on error
            return IntentClassification(
                intent="unknown",
                reasoning=f"Classification failed: {str(e)}",
                confidence=0.0
            )

    async def classify(
        self,
        question: str,
        context: Optional[str] = None
    ) -> IntentClassification:
        """
        Classify the user's intent.

        Args:
            question: The user's question
            context: Optional conversation context

        Returns:
            IntentClassification result
        """
        logger.debug(f"[{self.name}]: Classifying intent for '{question}'")

        context = context or "No previous context"

        try:
            messages = self._intent_prompt.format_messages(
                question=question,
                context=context,
                format_instructions=self._intent_parser.get_format_instructions()
            )

            # Use structured output
            response = await self._ainvoke(messages)

            # Parse the response
            result = self._intent_parser.parse(response.content)

            logger.info(
                f"[{self.name}]: Classified as '{result.intent}' "
                f"(confidence: {result.confidence})"
            )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Intent classification failed: {e}")
            # Return unknown intent on error
            return IntentClassification(
                intent="unknown",
                reasoning=f"Classification failed: {str(e)}",
                confidence=0.0
            )

    def check_ambiguity_sync(
        self,
        question: str
    ) -> AmbiguityDetection:
        """
        Check if the question is ambiguous (synchronous version).

        Args:
            question: The user's question

        Returns:
            AmbiguityDetection result
        """
        logger.debug(f"[{self.name}]: Checking ambiguity for '{question}'")

        try:
            messages = self._ambiguity_prompt.format_messages(
                question=question,
                format_instructions=self._ambiguity_parser.get_format_instructions()
            )

            response = self._invoke(messages)

            # Parse the response
            result = self._ambiguity_parser.parse(response.content)

            if result.is_ambiguous:
                logger.info(
                    f"[{self.name}]: Ambiguity detected: {result.ambiguity_type}"
                )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Ambiguity detection failed: {e}")
            # Return not ambiguous on error
            return AmbiguityDetection(
                is_ambiguous=False,
                ambiguity_type="none",
                clarification_question=""
            )

    async def check_ambiguity(
        self,
        question: str
    ) -> AmbiguityDetection:
        """
        Check if the question is ambiguous.

        Args:
            question: The user's question

        Returns:
            AmbiguityDetection result
        """
        logger.debug(f"[{self.name}]: Checking ambiguity for '{question}'")

        try:
            messages = self._ambiguity_prompt.format_messages(
                question=question,
                format_instructions=self._ambiguity_parser.get_format_instructions()
            )

            response = await self._ainvoke(messages)

            # Parse the response
            result = self._ambiguity_parser.parse(response.content)

            if result.is_ambiguous:
                logger.info(
                    f"[{self.name}]: Ambiguity detected: {result.ambiguity_type}"
                )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Ambiguity detection failed: {e}")
            # Return not ambiguous on error
            return AmbiguityDetection(
                is_ambiguous=False,
                ambiguity_type="none",
                clarification_question=""
            )

    def classify_full_sync(
        self,
        question: str,
        context: Optional[str] = None
    ) -> tuple[IntentClassification, Optional[AmbiguityDetection]]:
        """
        Classify intent and check ambiguity in one call (synchronous version).

        For query intents, also checks for ambiguity.

        Args:
            question: The user's question
            context: Optional conversation context

        Returns:
            Tuple of (intent_classification, ambiguity_detection)
            ambiguity_detection is None if intent is not 'query'
        """
        intent_result = self.classify_sync(question, context)

        ambiguity_result = None
        if intent_result.intent == "query":
            ambiguity_result = self.check_ambiguity_sync(question)

        return intent_result, ambiguity_result

    async def classify_full(
        self,
        question: str,
        context: Optional[str] = None
    ) -> tuple[IntentClassification, Optional[AmbiguityDetection]]:
        """
        Classify intent and check ambiguity in one call.

        For query intents, also checks for ambiguity.

        Args:
            question: The user's question
            context: Optional conversation context

        Returns:
            Tuple of (intent_classification, ambiguity_detection)
            ambiguity_detection is None if intent is not 'query'
        """
        intent_result = await self.classify(question, context)

        ambiguity_result = None
        if intent_result.intent == "query":
            ambiguity_result = await self.check_ambiguity(question)

        return intent_result, ambiguity_result
