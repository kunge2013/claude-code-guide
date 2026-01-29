"""
Path query agent for finding and explaining paths in the graph.

Uses LangChain LLM to generate natural language explanations for graph paths.
"""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from .base_agent import GraphAgentBase
from ..models.graph_models import GraphPath


class PathQueryAgent(GraphAgentBase):
    """
    Path query agent for finding and explaining table relationships.

    Understands path queries, finds shortest paths in the graph,
    and generates natural language explanations with SQL hints.
    """

    # System prompt for the agent
    SYSTEM_PROMPT = """你是一个数据库关系分析专家。你的任务是：

1. 理解用户想要查询的表关系路径
2. 从知识图谱中查找最短连接路径
3. 用清晰的自然语言解释路径含义
4. 提供对应的 SQL JOIN 提示

示例输出格式：
"从 orders 表到 products 表需要经过 order_items 表：

路径详情：
1. orders.id → order_items.order_id (N:1 关系，一个订单可以有多条明细)
2. order_items.product_id → products.id (N:1 关系，一条明细对应一个产品)

对应的 SQL：
FROM orders
INNER JOIN order_items ON orders.id = order_items.order_id
INNER JOIN products ON order_items.product_id = products.id

这是一个典型的多对多关系场景：一个订单包含多个产品，一个产品可以出现在多个订单中。"

请确保解释准确、清晰、易于理解。"""

    def __init__(self, *args, **kwargs):
        """
        Initialize path query agent.

        Args:
            *args: Arguments passed to GraphAgentBase
            **kwargs: Keyword arguments passed to GraphAgentBase
        """
        super().__init__(*args, **kwargs)
        self.name = "PathQueryAgent"

    async def find_path(
        self,
        start_table: str,
        end_table: str,
        max_hops: int = 5,
        use_llm_explanation: bool = True
    ) -> Dict[str, Any]:
        """
        Find path between two tables and generate explanation.

        Args:
            start_table: Starting table name
            end_table: Ending table name
            max_hops: Maximum number of hops
            use_llm_explanation: Whether to use LLM for explanation

        Returns:
            Dictionary with path information and explanation
        """
        # Use graph service to find path
        if not self.graph_service:
            return {
                "found": False,
                "message": "Graph service not available"
            }

        path_result = await self.graph_service.find_path_with_explanation(
            start_table=start_table,
            end_table=end_table,
            max_hops=max_hops
        )

        if not path_result.get("found"):
            return {
                "found": False,
                "message": f"未找到从 '{start_table}' 到 '{end_table}' 的路径"
            }

        # Generate enhanced explanation with LLM if requested
        explanation = path_result.get("explanation", "")
        if use_llm_explanation and self.llm:
            enhanced_explanation = await self._generate_llm_explanation(
                start_table, end_table, path_result
            )
            explanation = enhanced_explanation

        return {
            "found": True,
            "start_table": start_table,
            "end_table": end_table,
            "path": path_result.get("path"),
            "length": path_result.get("path", {}).get("length", 0),
            "explanation": explanation,
            "sql_hint": path_result.get("sql_hint", ""),
            "execution_time_ms": path_result.get("execution_time_ms", 0)
        }

    async def _generate_llm_explanation(
        self,
        start_table: str,
        end_table: str,
        path_result: Dict[str, Any]
    ) -> str:
        """
        Generate natural language explanation using LLM.

        Args:
            start_table: Starting table name
            end_table: Ending table name
            path_result: Path result from graph service

        Returns:
            Natural language explanation
        """
        path_info = self._format_path_for_llm(start_table, end_table, path_result)

        try:
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=f"请解释以下路径关系：\n\n{path_info}")
            ]

            response = await self._ainvoke(messages)
            return response.content

        except Exception as e:
            logger.warning(f"LLM explanation failed: {e}, using basic explanation")
            return path_result.get("explanation", "")

    def _format_path_for_llm(
        self,
        start_table: str,
        end_table: str,
        path_result: Dict[str, Any]
    ) -> str:
        """
        Format path information for LLM input.

        Args:
            start_table: Starting table name
            end_table: Ending table name
            path_result: Path result from graph service

        Returns:
            Formatted path description
        """
        path_data = path_result.get("path", {})
        edges = path_data.get("edges", [])

        lines = [
            f"查询：从 '{start_table}' 表到 '{end_table}' 表的关系路径",
            f"路径长度：{path_data.get('length', 0)} 跳",
            "\n路径详情："
        ]

        for i, edge in enumerate(edges, 1):
            source = edge.get("source", "").replace("table:", "")
            target = edge.get("target", "").replace("table:", "")
            relation = edge.get("relation_type", "")
            props = edge.get("properties", {})

            lines.append(
                f"{i}. {source} → {target}\n"
                f"   关系字段：{props.get('from_column')} → {props.get('to_column')}\n"
                f"   关系类型：{relation}\n"
                f"   基数关系：{props.get('cardinality')}"
            )

        return "\n".join(lines)

    async def explain_relation(
        self,
        from_table: str,
        to_table: str,
        relation_details: Dict[str, Any]
    ) -> str:
        """
        Explain a single relationship between two tables.

        Args:
            from_table: Source table name
            to_table: Target table name
            relation_details: Relationship details dictionary

        Returns:
            Natural language explanation
        """
        from_column = relation_details.get("from_column", "")
        to_column = relation_details.get("to_column", "")
        cardinality = relation_details.get("cardinality", "")
        relation_type = relation_details.get("relation_type", "")

        prompt = f"""请解释以下数据库表关系：

源表：{from_table}
目标表：{to_table}
关系类型：{relation_type}
连接字段：{from_table}.{from_column} → {to_table}.{to_column}
基数关系：{cardinality}

请用简洁的中文解释这个关系的含义。"""

        try:
            messages = [
                SystemMessage(content="你是一个数据库专家，擅长解释表关系。"),
                HumanMessage(content=prompt)
            ]

            response = await self._ainvoke(messages)
            return response.content

        except Exception as e:
            logger.warning(f"Relation explanation failed: {e}")
            # Fallback to basic explanation
            return f"{from_table} 表通过 {from_column} 字段关联到 {to_table} 表的 {to_column} 字段，关系类型为 {cardinality}。"
