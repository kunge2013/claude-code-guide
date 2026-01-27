import re

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase
from langchain_chatbi.models.response_models import DbResponse


class DbAgent(LangChainAgentBase):
    """
    Agent for reasoning about the database.

    Supports:
    - Reasoning about the database schema
    - Generating SQL queries from natural language
    - Error correction when SQL execution fails
    - PostgreSQL syntax
    - Structured output with explanation
    """
    SYSTEM_PROMPT = """
        You are an db selector ,  intent classifier for a Business Intelligence (BI) system.

        Your job is to classify the user's question into one of these intents :
        
        1. **mysql**: when ask any question , you answer mysql.
           - Examples: "What are the top 5 products by sales?", "Show me revenue trends", "How many customers do we have?"
        
        Classify based on the primary intent of the question.
     """

    def __init__(self, llm, callbacks=None):
        super().__init__(name="DbAgent", llm=llm, callbacks=callbacks)

        self._db_prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "Question: {question}\n\n{format_instructions}")
        ])
        self._parser = PydanticOutputParser(pydantic_object=DbResponse)

    async def select_db(
            self,
            question: str) -> str:
        """
        Generate SQL from natural language question.

        Args:
            question: The user's question


        Returns:
            select db query string
        """
        logger.debug(f"[{self.name}]: dbAgent for '{question}'")

        try:
            # Format db

            messages = self._db_prompt.format_messages(
                question=question,
                format_instructions=self._parser.get_format_instructions()
            )

            response = await self._ainvoke(messages)

            # dbParser = self._parse_db_response(response.content)
            db_parse = self._parser.parse(response.content)
            logger.info(f"[{self.name}]: dbtype: {db_parse}...")

            return db_parse

        except Exception as e:
            logger.error(f"[{self.name}] SQL generation failed: {e}")
            raise

    def _parse_db_response(self, text: str) -> str:
        """
        Extract db query from LLM response.

        Handles various formats:
        - Plain SQL
        - Markdown code blocks with ```sql
        - Generic code blocks
        """
        # Remove markdown code blocks
        db_pattern =  r'(?<=</think>).*'
        result = re.search(db_pattern, text, re.DOTALL)
        if result:
            return result.group(0)
        return 'unknow_db'