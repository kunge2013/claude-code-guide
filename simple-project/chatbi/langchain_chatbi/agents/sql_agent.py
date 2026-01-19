"""
SQL Generation Agent

Generates SQL queries from natural language questions with error correction support.
Uses PostgreSQL syntax and supports retry logic when SQL execution fails.
"""

import re
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase
from langchain_chatbi.models.response_models import SQLGeneration


class SqlAgent(LangChainAgentBase):
    """
    Agent for generating SQL queries from natural language.

    Supports:
    - Initial SQL generation from natural language
    - Error correction when SQL execution fails
    - PostgreSQL syntax
    - Structured output with explanation
    """

    SYSTEM_PROMPT = """You are a PostgreSQL expert. Generate SQL queries to answer questions based on the provided table schema.

===Response Guidelines===
1. CRITICAL: You MUST generate a valid SQL query. Do NOT return explanations or error messages.
2. CRITICAL: Do NOT query information_schema or system catalogs. Use the provided table schema above.
3. If the provided context is sufficient, please generate a valid SQL query without any explanations.
4. If you're unsure about column names, make educated guesses based on the schema provided.
5. Please use the most relevant table(s) from the schema provided above.
6. Ensure that the output SQL is PostgreSQL-compliant and executable, and free of syntax errors.
7. For TOP N queries, use ORDER BY and LIMIT clauses.
8. Your response should contain ONLY the SQL query, nothing else.

===Table Schema===
{table_schema}
"""

    CORRECTION_SYSTEM_PROMPT = """You are a PostgreSQL expert. Fix the failed SQL query below.

===Table Schema===
{table_schema}

===Instructions===
1. Fix the error while maintaining the original intent.
2. Use valid PostgreSQL syntax.
3. Output ONLY the corrected SQL query. No explanation."""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the SqlAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="SqlAgent", llm=llm, callbacks=callbacks)

        # SQL generation prompt
        self._sql_prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "Question: {question}")
        ])

        # Error correction prompt
        self._correction_prompt = ChatPromptTemplate.from_messages([
            ("system", self.CORRECTION_SYSTEM_PROMPT),
            ("human", "Question: {question}\nFailed SQL: {sql}\nError: {error}")
        ])

        self._parser = PydanticOutputParser(pydantic_object=SQLGeneration)

    async def generate_sql(
        self,
        question: str,
        table_schemas: List[Dict[str, Any]],
        few_shots: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate SQL from natural language question.

        Args:
            question: The user's question
            table_schemas: List of relevant table schemas
            few_shots: Optional few-shot examples

        Returns:
            Generated SQL query string
        """
        logger.debug(f"[{self.name}]: Generating SQL for '{question}'")

        try:
            # Format table schemas
            formatted_schemas = self._format_schemas(table_schemas)

            messages = self._sql_prompt.format_messages(
                table_schema=formatted_schemas,
                question=question
            )

            # Add few-shot examples if provided
            if few_shots:
                messages = self._add_few_shots(messages, few_shots)

            response = await self._ainvoke(messages)

            # Extract SQL from response
            sql = self._extract_sql(response.content)

            logger.info(f"[{self.name}]: Generated SQL: {sql[:100]}...")

            return sql

        except Exception as e:
            logger.error(f"[{self.name}] SQL generation failed: {e}")
            raise

    async def correct_sql(
        self,
        question: str,
        sql: str,
        error: str,
        table_schemas: List[Dict[str, Any]]
    ) -> str:
        """
        Correct SQL based on error message.

        Args:
            question: The original question
            sql: The failed SQL query
            error: The error message from database
            table_schemas: List of relevant table schemas

        Returns:
            Corrected SQL query string
        """
        logger.debug(f"[{self.name}]: Correcting SQL. Error: {error[:100]}...")

        try:
            # Format table schemas
            formatted_schemas = self._format_schemas(table_schemas)

            messages = self._correction_prompt.format_messages(
                table_schema=formatted_schemas,
                question=question,
                sql=sql,
                error=error
            )

            response = await self._ainvoke(messages)

            # Extract corrected SQL
            corrected_sql = self._extract_sql(response.content)

            logger.info(f"[{self.name}]: Corrected SQL: {corrected_sql[:100]}...")

            return corrected_sql

        except Exception as e:
            logger.error(f"[{self.name}] SQL correction failed: {e}")
            # Return original SQL if correction fails
            return sql

    def _format_schemas(self, table_schemas: List[Dict[str, Any]]) -> str:
        """Format table schemas for prompt."""
        formatted = []
        for table in table_schemas:
            name = table.get("name", "unknown")
            columns = table.get("columns", [])

            # Format columns
            if isinstance(columns, list):
                col_desc = ", ".join([
                    f"{col.get('name', '?')} {col.get('type', 'unknown')}"
                    for col in columns
                ])
            else:
                col_desc = str(columns)

            formatted.append(f"Table: {name} ({col_desc})")

        return "\n".join(formatted)

    def _add_few_shots(
        self,
        messages: List,
        few_shots: List[Dict[str, str]]
    ) -> List:
        """Add few-shot examples to messages."""
        # Insert few-shot examples before the final user message
        result = messages[:-1]  # All but last message

        for shot in few_shots:
            if "question" in shot and "sql" in shot:
                from langchain_core.messages import HumanMessage, AIMessage
                result.append(HumanMessage(content=shot["question"]))
                result.append(AIMessage(content=shot["sql"]))

        result.append(messages[-1])  # Add back the final user message
        return result

    def _extract_sql(self, text: str) -> str:
        """
        Extract SQL query from LLM response.

        Handles various formats:
        - Plain SQL
        - Markdown code blocks with ```sql
        - Generic code blocks
        """
        # Remove markdown code blocks
        sql_pattern = r"```(?:sql)?\s*\n?(.*?)\n?```"
        matches = re.findall(sql_pattern, text, re.DOTALL | re.IGNORECASE)

        if matches:
            return matches[0].strip()

        # Look for SELECT statement (case insensitive)
        select_pattern = r"(SELECT[\s\S]*?)(?:\n\n|\Z)"
        select_matches = re.findall(select_pattern, text, re.IGNORECASE)

        if select_matches:
            return select_matches[0].strip()

        # Fallback: return the whole text, cleaned up
        cleaned = text.strip()
        # Remove common prefixes
        if cleaned.lower().startswith(("here is the sql", "the sql is", "sql:")):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned

        return cleaned
