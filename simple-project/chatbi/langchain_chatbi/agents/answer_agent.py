"""
Answer Summarization Agent

Generates natural language summaries from query results with streaming support.

Provides:
- Concise data summaries
- Key insights and findings
- Actionable recommendations (optional)
- Multi-language support (zh-CN, en-US)
"""

import json
from typing import AsyncGenerator, Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from langchain_chatbi.agents.base import LangChainAgentBase


class AnswerSummarizationAgent(LangChainAgentBase):
    """
    Agent for generating natural language answers from query results.

    Creates comprehensive, professional summaries of BI query results
    with multi-language support and streaming output.
    """

    ZH_CN_PROMPT = """你是一个数据分析专家。用简洁、专业的中文总结查询结果。

### 输出要求 ###
1. **开头**: 直接回答用户问题（1-2句话）
2. **数据摘要**: 关键发现和数字（3-5个要点）
3. **洞察**: 数据背后的含义（可选，如果有明显趋势或异常）
4. **语气**: 专业、客观、易懂

### 示例 ###
问题: "2023年销售额最高的5个产品是什么？"

答案:
根据分析，2023年销售额最高的5个产品如下：

**核心发现**:
• 产品A以1,250万元位居榜首，占总销售额的28%
• 前三名产品（A、B、C）贡献了总销售额的65%
• 产品E虽然排名第五，但增长率达到45%，表现突出

**数据详情**:
1. 产品A: ¥12,500,000
2. 产品B: ¥9,800,000
3. 产品C: ¥8,600,000
4. 产品D: ¥6,200,000
5. 产品E: ¥5,500,000

这些产品占据了公司2023年总销售额的75%，是业务的核心驱动力。
"""

    EN_US_PROMPT = """You are a data analysis expert. Summarize the query results concisely and professionally.

### OUTPUT REQUIREMENTS ###
1. **Opening**: Directly answer the user's question (1-2 sentences)
2. **Data Summary**: Key findings with numbers (3-5 bullet points)
3. **Insights**: What the data means (optional, if clear trends/anomalies)
4. **Tone**: Professional, objective, clear

### EXAMPLE ###
Question: "What are the top 5 products by sales in 2023?"

Answer:
Based on the analysis, here are the top 5 products by sales in 2023:

**Key Findings**:
• Product A leads with $12.5M, accounting for 28% of total sales
• Top 3 products (A, B, C) contribute 65% of total revenue
• Product E ranks 5th but shows impressive 45% growth rate

**Data Details**:
1. Product A: $12,500,000
2. Product B: $9,800,000
3. Product C: $8,600,000
4. Product D: $6,200,000
5. Product E: $5,500,000

These products represent 75% of the company's 2023 revenue and are core business drivers.
"""

    def __init__(self, llm, callbacks=None):
        """
        Initialize the AnswerSummarizationAgent.

        Args:
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers
        """
        super().__init__(name="AnswerSummarizationAgent", llm=llm, callbacks=callbacks)

        self._zh_prompt = ChatPromptTemplate.from_messages([
            ("system", self.ZH_CN_PROMPT),
            ("human", """### USER'S QUESTION ###
{question}

### QUERY CONTEXT ###
```json
{query_metadata}
```

### QUERY RESULTS ###
```json
{result_data}
```
Total rows: {row_count}

### CHART TYPE ###
{chart_type} - {chart_description}

### YOUR TASK ###
Write a comprehensive answer following the format above. Focus on:
- Direct answer to the question
- Key numbers and comparisons
- Notable patterns or trends
- Actionable insights (if applicable)

Start writing the answer now:""")
        ])

        self._en_prompt = ChatPromptTemplate.from_messages([
            ("system", self.EN_US_PROMPT),
            ("human", """### USER'S QUESTION ###
{question}

### QUERY CONTEXT ###
```json
{query_metadata}
```

### QUERY RESULTS ###
```json
{result_data}
```
Total rows: {row_count}

### CHART TYPE ###
{chart_type} - {chart_description}

### YOUR TASK ###
Write a comprehensive answer following the format above. Focus on:
- Direct answer to the question
- Key numbers and comparisons
- Notable patterns or trends
- Actionable insights (if applicable)

Start writing the answer now:""")
        ])

    async def generate_answer(
        self,
        question: str,
        query_metadata: Dict[str, Any],
        result_data: List[Dict],
        chart_config: Dict[str, Any],
        language: str = "zh-CN"
    ) -> str:
        """
        Generate natural language answer from query results (non-streaming).

        Args:
            question: User's question
            query_metadata: Executed query metadata
            result_data: Query results
            chart_config: Generated chart config
            language: Output language (zh-CN or en-US)

        Returns:
            Complete answer as string
        """
        logger.debug(f"[{self.name}]: Generating answer for '{question[:50]}...'")

        try:
            # Select prompt based on language
            prompt = self._zh_prompt if language == "zh-CN" else self._en_prompt

            messages = prompt.format_messages(
                question=question,
                query_metadata=json.dumps(query_metadata, indent=2, ensure_ascii=False),
                result_data=json.dumps(result_data[:10], indent=2, ensure_ascii=False),
                row_count=len(result_data),
                chart_type=chart_config.get("chartType", "table"),
                chart_description=chart_config.get("description", "")
            )

            response = await self._ainvoke(messages)

            logger.info(f"[{self.name}]: Answer generation completed")

            return response.content

        except Exception as e:
            logger.error(f"[{self.name}] Answer generation failed: {e}")
            return self._get_fallback_answer(result_data, language)

    async def generate_answer_stream(
        self,
        question: str,
        query_metadata: Dict[str, Any],
        result_data: List[Dict],
        chart_config: Dict[str, Any],
        language: str = "zh-CN"
    ) -> AsyncGenerator[str, None]:
        """
        Generate natural language answer with streaming output.

        Args:
            question: User's question
            query_metadata: Executed query metadata
            result_data: Query results
            chart_config: Generated chart config
            language: Output language (zh-CN or en-US)

        Yields:
            String chunks of answer as they are generated
        """
        logger.debug(f"[{self.name}]: Generating answer (streaming) for '{question[:50]}...'")

        try:
            # Select prompt based on language
            prompt = self._zh_prompt if language == "zh-CN" else self._en_prompt

            messages = prompt.format_messages(
                question=question,
                query_metadata=json.dumps(query_metadata, indent=2, ensure_ascii=False),
                result_data=json.dumps(result_data[:10], indent=2, ensure_ascii=False),
                row_count=len(result_data),
                chart_type=chart_config.get("chartType", "table"),
                chart_description=chart_config.get("description", "")
            )

            accumulated_length = 0

            async for chunk in self._astream(messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                accumulated_length += len(content)
                yield content

            logger.info(f"[{self.name}]: Answer streaming completed ({accumulated_length} chars)")

        except Exception as e:
            logger.error(f"[{self.name}] Answer streaming failed: {e}")
            yield self._get_fallback_answer(result_data, language)

    def _get_fallback_answer(
        self,
        result_data: List[Dict],
        language: str = "zh-CN"
    ) -> str:
        """
        Generate simple fallback answer on error.

        Args:
            result_data: Query results
            language: Output language

        Returns:
            Fallback answer string
        """
        row_count = len(result_data)

        if language == "zh-CN":
            return f"查询成功完成，共找到 {row_count} 条记录。详细数据请查看上方的图表和表格。"
        else:
            return f"Query completed successfully with {row_count} records found. Please see the chart and table above for details."
