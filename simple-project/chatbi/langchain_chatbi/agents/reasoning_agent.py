"""
Query Reasoning Agent

Generates step-by-step reasoning plan for query execution with streaming support.

This agent:
1. Analyzes the user's question
2. Identifies required data models, metrics, and filters
3. Breaks down the query into logical steps
4. Provides transparency into the AI's thinking process

Supports streaming for real-time display of reasoning steps.
"""

from typing import AsyncGenerator, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase


class QueryReasoningAgent(LangChainAgentBase):
    """
    Agent for generating query reasoning plans.

    Creates detailed step-by-step reasoning plans for Business Intelligence queries.
    Supports both non-streaming and streaming modes.
    """

    SYSTEM_PROMPT = """You are a Business Intelligence query planner.

Given a user's question and available data models, generate a DETAILED step-by-step reasoning plan to answer the question.

### AVAILABLE DATA MODELS ###
{mdl_context}

### SIMILAR HISTORICAL QUERIES ###
{history_queries}

### USER'S QUESTION ###
{question}

### YOUR TASK ###
Think step-by-step and create a reasoning plan:

1. **Understand the Question**
   - What is the user asking for?
   - What are the key metrics/dimensions involved?
   - What time period or filters are mentioned?

2. **Identify Required Data**
   - Which models/tables are needed?
   - Which columns (measures and dimensions)?
   - What aggregations are required?

3. **Define Query Logic**
   - How to group the data?
   - How to filter the data?
   - How to sort the results?
   - How many rows to return?

4. **Expected Output**
   - What format should the result be in?
   - What chart type is most appropriate?

### OUTPUT FORMAT ###
Write your reasoning in clear, numbered steps. Be specific about model names, column names, and logic.
Use markdown formatting for readability.

Example:
## Step 1: Understanding the Question
The user wants to find the top 5 products by total sales revenue in 2023.

## Step 2: Identify Required Data
- Model: Orders
- Measure: total_amount (aggregation: sum)
- Dimension: product_name
- Time filter: order_date in 2023

## Step 3: Query Logic
- Group by: product_name
- Aggregate: SUM(total_amount)
- Filter: order_date >= 2023-01-01 AND order_date <= 2023-12-31
- Sort: SUM(total_amount) DESC
- Limit: 5

## Step 4: Expected Output
- Top 5 products with their total revenue
- Best chart: Horizontal bar chart
"""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the QueryReasoningAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="QueryReasoningAgent", llm=llm, callbacks=callbacks)

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Business Intelligence query planner. Generate detailed step-by-step reasoning plans."),
            ("human", self.SYSTEM_PROMPT)
        ])

    async def generate_reasoning(
        self,
        question: str,
        mdl_context: str = "",
        history_queries: str = ""
    ) -> str:
        """
        Generate reasoning plan for a query (non-streaming).

        Args:
            question: User's natural language question
            mdl_context: Retrieved MDL context (models/columns)
            history_queries: Similar historical queries (optional)

        Returns:
            Complete reasoning plan as string
        """
        logger.debug(f"[{self.name}]: Generating reasoning for '{question[:50]}...'")

        try:
            messages = self._prompt.format_messages(
                question=question,
                mdl_context=mdl_context or "No data models available",
                history_queries=history_queries or "No historical queries available"
            )

            response = await self._ainvoke(messages)

            logger.info(f"[{self.name}]: Reasoning generation completed")

            return response.content

        except Exception as e:
            logger.error(f"[{self.name}] Reasoning generation failed: {e}")
            return f"Failed to generate reasoning: {str(e)}"

    async def generate_reasoning_stream(
        self,
        question: str,
        mdl_context: str = "",
        history_queries: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        Generate reasoning plan with streaming output.

        Args:
            question: User's natural language question
            mdl_context: Retrieved MDL context
            history_queries: Similar historical queries

        Yields:
            String chunks of reasoning as they are generated
        """
        logger.debug(f"[{self.name}]: Generating reasoning (streaming) for '{question[:50]}...'")

        try:
            messages = self._prompt.format_messages(
                question=question,
                mdl_context=mdl_context or "No data models available",
                history_queries=history_queries or "No historical queries available"
            )

            accumulated_length = 0

            async for chunk in self._astream(messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                accumulated_length += len(content)
                yield content

            logger.info(f"[{self.name}]: Reasoning streaming completed ({accumulated_length} chars)")

        except Exception as e:
            logger.error(f"[{self.name}] Reasoning streaming failed: {e}")
            yield f"Error: {str(e)}"
