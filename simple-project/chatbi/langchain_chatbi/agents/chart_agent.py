"""
Chart Generation Agent

Generates chart configurations from query results.

Supports multiple chart types:
- bar: Categorical comparisons
- line: Trends over time
- pie: Proportions/percentages
- area: Trends with emphasis on volume
- scatter: Correlation analysis
- table: Raw data display

Uses auto-detection for simple cases and LLM for complex ones.
"""

import json
import re
from typing import Dict, Any, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase
from langchain_chatbi.models.response_models import ChartConfig


class ChartGenerationAgent(LangChainAgentBase):
    """
    Agent for generating chart configurations from query results.

    Combines rule-based auto-detection for simple cases with LLM-based
    generation for complex visualization needs.
    """

    SYSTEM_PROMPT = """You are a data visualization expert. Generate the BEST chart configuration for the given data.

### USER'S QUESTION ###
{question}

### QUERY CONTEXT ###
```json
{query_metadata}
```

### QUERY RESULT (first 5 rows) ###
```json
{result_data}
```

### RESULT SUMMARY ###
Total rows: {row_count}

### CHART TYPE SELECTION RULES ###

**bar**: Use for categorical comparisons
- Example: Sales by product, revenue by region
- Requirements: 1+ categorical dimension, 1+ measure
- Best for: <20 categories

**line**: Use for trends over time
- Example: Sales over months, user growth
- Requirements: 1 time dimension, 1+ measure
- Best for: Time series data

**pie**: Use for proportions/percentages
- Example: Market share, category distribution
- Requirements: 1 categorical dimension, 1 measure
- Best for: <7 categories, sum = 100% or meaningful total

**area**: Use for trends with volume emphasis
- Example: Cumulative sales, stacked categories over time
- Requirements: 1 time dimension, 1+ measure
- Best for: Emphasizing magnitude/volume

**scatter**: Use for correlation analysis
- Example: Sales vs profit margin
- Requirements: 2+ measures
- Best for: Finding relationships between metrics

**table**: Use as fallback
- When no clear pattern
- When user asks for "detailed data" or "list"
- When data is too complex for charts

### YOUR TASK ###
Analyze the data structure and choose the MOST APPROPRIATE chart type.

Return a JSON object with chart configuration."""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the ChartGenerationAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="ChartGenerationAgent", llm=llm, callbacks=callbacks)

        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{question}\n\n{query_metadata}\n\n{result_data}\n\nTotal rows: {row_count}")
        ])

        self._parser = PydanticOutputParser(pydantic_object=ChartConfig)

    async def generate_chart(
        self,
        question: str,
        query_metadata: Dict[str, Any],
        result_data: List[Dict],
        result_summary: str = ""
    ) -> ChartConfig:
        """
        Generate chart configuration from query results.

        Args:
            question: User's question
            query_metadata: Executed query metadata
            result_data: Query result data
            result_summary: Optional summary of results

        Returns:
            ChartConfig object
        """
        logger.debug(f"[{self.name}]: Generating chart for '{question[:50]}...'")

        try:
            # Auto-detect simple cases without LLM
            auto_config = self._auto_detect_chart(
                query_metadata=query_metadata,
                result_data=result_data,
                question=question,
            )

            if auto_config and not self._should_use_llm(question):
                logger.info(f"[{self.name}]: Auto-detected chart type: {auto_config.chartType}")
                return auto_config

            # Use LLM for complex cases
            logger.debug(f"[{self.name}]: Using LLM for chart generation")

            messages = self._prompt.format_messages(
                question=question,
                query_metadata=json.dumps(query_metadata, indent=2, ensure_ascii=False),
                result_data=json.dumps(result_data[:5], indent=2, ensure_ascii=False),
                row_count=len(result_data)
            )

            response = await self._ainvoke(messages)

            # Parse the structured response
            chart_config = self._parser.parse(response.content)

            logger.info(f"[{self.name}]: Generated chart: {chart_config.chartType}")

            return chart_config

        except Exception as e:
            logger.error(f"[{self.name}] Chart generation failed: {e}")
            # Return fallback table config
            return self._get_fallback_config(result_data)

    def _auto_detect_chart(
        self,
        query_metadata: Dict[str, Any],
        result_data: List[Dict],
        question: str,
    ) -> Optional[ChartConfig]:
        """
        Auto-detect chart type based on data structure.

        Args:
            query_metadata: Query metadata
            result_data: Result data
            question: User question

        Returns:
            ChartConfig or None if can't determine
        """
        if not result_data:
            return None

        measures = query_metadata.get("measures", [])
        dimensions = query_metadata.get("dimensions", [])
        time_dimensions = query_metadata.get("timeDimensions", [])

        # Get column names from first row
        columns = list(result_data[0].keys())
        row_count = len(result_data)

        # Time series with time dimension → line chart
        if time_dimensions and len(time_dimensions) > 0:
            time_col = columns[0]
            value_col = columns[1] if len(columns) > 1 else columns[0]

            return ChartConfig(
                chartType="line",
                title=self._generate_title(question, "line"),
                description=f"Trend analysis with {row_count} data points",
                spec=self._create_spec(xField=time_col, yField=value_col)
            )

        # Single measure + single dimension, small cardinality → bar chart
        if (
            len(measures) == 1
            and len(dimensions) == 1
            and row_count <= 20
            and row_count >= 2
        ):
            dim_col = columns[0]
            measure_col = columns[1] if len(columns) > 1 else columns[0]

            return ChartConfig(
                chartType="bar",
                title=self._generate_title(question, "bar"),
                description=f"Comparison across {row_count} categories",
                spec=self._create_spec(xField=dim_col, yField=measure_col)
            )

        # Pie chart keywords
        if any(
            kw in question.lower()
            for kw in ["proportion", "percentage", "share", "distribution", "占比", "比例"]
        ):
            if len(dimensions) == 1 and len(measures) == 1 and row_count <= 7:
                dim_col = columns[0]
                measure_col = columns[1] if len(columns) > 1 else columns[0]

                from langchain_chatbi.models.response_models import ChartSpec
                return ChartConfig(
                    chartType="pie",
                    title=self._generate_title(question, "pie"),
                    description=f"Distribution across {row_count} categories",
                    spec=ChartSpec(
                        angleField=measure_col,
                        colorField=dim_col
                    )
                )

        # Too many rows or complex structure → table
        if row_count > 50 or len(columns) > 5:
            from langchain_chatbi.models.response_models import ChartSpec
            return ChartConfig(
                chartType="table",
                title=self._generate_title(question, "table"),
                description=f"Detailed data view with {row_count} rows",
                spec=ChartSpec()
            )

        return None

    def _should_use_llm(self, question: str) -> bool:
        """Determine if LLM is needed for chart selection."""
        complex_keywords = [
            "compare", "trend", "correlation", "relationship", "analyze",
            "对比", "趋势", "相关", "关系", "分析",
        ]
        return any(kw in question.lower() for kw in complex_keywords)

    def _generate_title(self, question: str, chart_type: str) -> str:
        """Generate simple title from question."""
        title = question[:50]
        if len(question) > 50:
            title += "..."
        return title

    def _create_spec(self, **fields) -> "ChartSpec":
        """Create ChartSpec from field arguments."""
        from langchain_chatbi.models.response_models import ChartSpec
        return ChartSpec(**{k: v for k, v in fields.items() if v is not None})

    def _get_fallback_config(self, result_data: List[Dict]) -> ChartConfig:
        """Get fallback table configuration."""
        from langchain_chatbi.models.response_models import ChartSpec

        columns = list(result_data[0].keys()) if result_data else []

        return ChartConfig(
            chartType="table",
            title="Query Results",
            description=f"Data table with {len(result_data)} rows",
            spec=ChartSpec()
        )
