"""
Diagnosis Agent

Extracts insights and key findings from query results.

Provides:
- Concise data summaries (2-3 sentences)
- Key observations and trends (3-5 bullet points)
- Business value insights
"""

import json
from typing import List, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase
from langchain_chatbi.models.response_models import InsightSummary


class DiagnosisAgent(LangChainAgentBase):
    """
    Agent for extracting insights from query results.

    Analyzes data samples to provide business-relevant insights
    and key findings.
    """

    SYSTEM_PROMPT = """You are a Data Analyst expert. Your task is to analyze the provided data sample for the given question and SQL.

===Response Guidelines===
1. Provide a clear, concise summary of the answer (2-3 sentences).
2. Identify key trends, anomalies, or interesting facts (3-5 bullet points).
3. Focus on business value and insights, not just describing the numbers.
4. Do NOT verify the SQL correctness, assume the data is correct.
5. Output your analysis as a structured response.

### INPUT ###
Question: {question}
SQL: {sql}

### DATA SAMPLE ###
{data_sample}

Total rows: {row_count}

### YOUR TASK ###
Analyze the data and provide:
1. A summary of what the data shows
2. Key observations, trends, or patterns

Focus on actionable insights that help understand the business implications."""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the DiagnosisAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="DiagnosisAgent", llm=llm, callbacks=callbacks)

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Data Analyst expert. Analyze data and provide insights."),
            ("human", "{format_instructions}\n\n" + self.SYSTEM_PROMPT)
        ])

        self._parser = PydanticOutputParser(pydantic_object=InsightSummary)

    async def generate_diagnosis(
        self,
        question: str,
        sql: str,
        data_sample: List[Dict],
        language: str = "English"
    ) -> InsightSummary:
        """
        Generate insights from data.

        Args:
            question: The user's original question
            sql: The executed SQL query
            data_sample: Sample of the data returned (up to 20 rows)
            language: Output language

        Returns:
            InsightSummary with summary and key_points
        """
        logger.debug(f"[{self.name}]: Generating diagnosis for '{question[:50]}...'")

        try:
            # Format data sample for prompt
            formatted_sample = json.dumps(data_sample[:20], indent=2, ensure_ascii=False)

            messages = self._prompt.format_messages(
                question=question,
                sql=sql,
                data_sample=formatted_sample,
                row_count=len(data_sample),
                format_instructions=self._parser.get_format_instructions()
            )

            response = await self._ainvoke(messages)

            # Parse the structured response
            insight = self._parser.parse(response.content)

            logger.info(f"[{self.name}]: Diagnosis generated with {len(insight.key_points)} key points")

            return insight

        except Exception as e:
            logger.error(f"[{self.name}] Diagnosis generation failed: {e}")

            # Check if it's a timeout error
            error_str = str(e).lower()
            is_timeout = "timeout" in error_str or "timed out" in error_str

            if is_timeout:
                logger.warning(f"[{self.name}]: Diagnosis generation timed out")
                return InsightSummary(
                    summary="Analysis took too long to generate. Please try again later.",
                    key_points=[],
                    confidence=0.0
                )
            else:
                return InsightSummary(
                    summary="Unable to generate insights due to an error.",
                    key_points=[],
                    confidence=0.0
                )
