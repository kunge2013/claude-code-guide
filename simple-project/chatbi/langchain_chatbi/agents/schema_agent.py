"""
Schema Selection Agent

Selects relevant table schemas from the available options based on the user's question.
This reduces the context for SQL generation by filtering to only relevant tables.
"""

import json
from typing import List, Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase
from langchain_chatbi.models.response_models import SchemaSelection


class SchemaAgent(LangChainAgentBase):
    """
    Agent for selecting relevant table schemas.

    Given a user's question and a list of available table schemas,
    selects only the tables that are relevant to answering the question.
    """

    SYSTEM_PROMPT = """You are a database schema selector for a Business Intelligence system.

Your job is to analyze the user's question and select which database tables are relevant to answering it.

You will be given:
1. The user's question
2. A list of available database tables with their columns

You should:
1. Identify which tables contain data relevant to the question
2. Explain why each selected table is relevant
3. Exclude tables that are not needed

Be selective - only include tables that are truly necessary for answering the question.
If a question can be answered with a single table, don't include unrelated tables."""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the SchemaAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="SchemaAgent", llm=llm, callbacks=callbacks)

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", """Question: {question}

Available Tables:
{table_schemas}

Select the tables that are relevant to answering this question.

{format_instructions}""")
        ])

        self._parser = PydanticOutputParser(pydantic_object=SchemaSelection)

    async def select_schemas(
        self,
        question: str,
        table_schemas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Select relevant table schemas from the available options.

        Args:
            question: The user's question
            table_schemas: List of available table schemas (each with 'name' and 'columns')

        Returns:
            List of selected table schemas (filtered from input)
        """
        logger.debug(f"[{self.name}]: Selecting schemas for '{question}'")
        logger.debug(f"[{self.name}]: Available tables: {len(table_schemas)}")

        try:
            # Format table schemas for the prompt
            formatted_schemas = self._format_schemas(table_schemas)

            messages = self._prompt.format_messages(
                question=question,
                table_schemas=formatted_schemas,
                format_instructions=self._parser.get_format_instructions()
            )

            response = await self._ainvoke(messages)

            # Parse the structured response
            result = self._parser.parse(response.content)

            # Extract the selected table names
            selected_names = {table.name for table in result.tables}

            logger.info(
                f"[{self.name}]: Selected {len(selected_names)} tables: {selected_names}"
            )

            # Filter the original schemas to only selected ones
            selected_schemas = [
                schema for schema in table_schemas
                if schema.get("name") in selected_names
            ]

            return selected_schemas

        except Exception as e:
            logger.error(f"[{self.name}] Schema selection failed: {e}")
            # Fallback: return all schemas if selection fails
            logger.warning(f"[{self.name}]: Falling back to all schemas")
            return table_schemas

    def _format_schemas(self, table_schemas: List[Dict[str, Any]]) -> str:
        """
        Format table schemas for inclusion in the prompt.

        Args:
            table_schemas: List of table schema dictionaries

        Returns:
            Formatted string representation
        """
        formatted = []
        for table in table_schemas:
            name = table.get("name", "unknown")
            columns = table.get("columns", [])

            # Format columns
            if isinstance(columns, list):
                col_desc = ", ".join([
                    f"{col.get('name', '?')} ({col.get('type', 'unknown')})"
                    for col in columns
                ])
            else:
                col_desc = str(columns)

            formatted.append(f"- {name}: {col_desc}")

        return "\n".join(formatted)

    async def select_schemas_raw(
        self,
        question: str,
        table_schemas_json: str
    ) -> List[Dict[str, Any]]:
        """
        Select schemas when input is provided as JSON string.

        Args:
            question: The user's question
            table_schemas_json: JSON string of table schemas

        Returns:
            List of selected table schemas
        """
        try:
            table_schemas = json.loads(table_schemas_json)
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Failed to parse table_schemas JSON: {e}")
            raise ValueError(f"Invalid table_schemas JSON: {e}")

        return await self.select_schemas(question, table_schemas)
