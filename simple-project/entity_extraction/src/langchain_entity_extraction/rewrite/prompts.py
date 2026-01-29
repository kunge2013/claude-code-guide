"""Prompt templates for question rewriting."""

# System prompt for the question rewriter
SYSTEM_PROMPT = """你是一个专业的问题改写助手。你的任务是将用户的自然语言问题改写成结构化、明确的问题，以便后续的实体识别和SQL生成。

改写规则：
1. **时间规范化**：将相对时间表达转换为明确的绝对时间
   - 今年 → 具体年份（如2026年）
   - 上月 → 具体年月（如2025年12月）
   - 去年 → 去年年份（如2025年）
   - 本季度 → 具体季度（如2026年Q1）

2. **产品ID规范化**：将产品简称或别名转换为标准的产品ID表达
   - cdn → 产品ID为cdn
   - ecs → 产品ID为ecs
   - oss → 产品ID为oss

3. **字段明确化**：将模糊的字段描述转换为明确的字段名
   - 金额 → 出账金额
   - 数量 → 订单数量
   - 收入 → 营业收入

4. **结构化重组**：将问题改写为结构化的查询模式
   模式："{实体类型}为{值}，{条件}的{指标}是多少"

5. **语义一致性**：保持问题的语义不变，只增强表达的明确性

输出格式要求：
请严格按照以下JSON格式输出：
{{
    "rewritten": "改写后的问题",
    "entities": {{
        "product_id": "产品ID（如果有）",
        "time": "时间信息（如果有）",
        "field": "字段名（如果有）"
    }},
    "reasoning": "改写的推理过程",
    "changes_made": ["改动1", "改动2", ...]
}}

注意：
- 如果某个实体类型不存在，对应字段设为null
- changes_made应该列出所有主要的改动
- reasoning应该简要说明改写的逻辑
"""

# User prompt template
USER_PROMPT_TEMPLATE = """请改写以下问题：

**原始问题**：{question}

**当前日期**：{current_date}
**当前年份**：{current_year}
**当前月份**：{current_month}

**可用产品列表**：{product_list}
**可用字段列表**：{field_list}

请严格按照系统提示词要求的JSON格式输出改写结果。
"""

# Simplified prompt for basic rewriting
SIMPLE_PROMPT_TEMPLATE = """请改写以下问题，使其更加明确和结构化：

原始问题：{question}

改写要求：
1. 将相对时间（如"今年"、"上月"）转换为具体时间
2. 将产品简称（如"cdn"）转换为完整表达（如"产品ID为cdn"）
3. 将模糊字段（如"金额"）转换为明确字段（如"出账金额"）

当前日期：{current_date}

请以JSON格式输出：
{{
    "rewritten": "改写后的问题",
    "entities": {{"product_id": "...", "time": "...", "field": "..."}},
    "reasoning": "改写说明"
}}
"""


def get_system_prompt() -> str:
    """Get the system prompt for question rewriting.

    Returns:
        System prompt string
    """
    return SYSTEM_PROMPT


def get_user_prompt(
    question: str,
    current_date: str,
    current_year: int,
    current_month: int,
    product_list: str = None,
    field_list: str = None
) -> str:
    """Get the user prompt for question rewriting.

    Args:
        question: The original question to rewrite
        current_date: Current date string
        current_year: Current year
        current_month: Current month (1-12)
        product_list: Available products (comma-separated)
        field_list: Available fields (comma-separated)

    Returns:
        User prompt string
    """
    if product_list is None:
        product_list = "cdn, ecs, oss, rds"

    if field_list is None:
        field_list = "出账金额, 订单数量, 营业收入, 用户数"

    return USER_PROMPT_TEMPLATE.format(
        question=question,
        current_date=current_date,
        current_year=current_year,
        current_month=current_month,
        product_list=product_list,
        field_list=field_list
    )


def get_simple_prompt(question: str, current_date: str) -> str:
    """Get a simplified prompt for basic question rewriting.

    Args:
        question: The original question to rewrite
        current_date: Current date string

    Returns:
        Simplified prompt string
    """
    return SIMPLE_PROMPT_TEMPLATE.format(
        question=question,
        current_date=current_date
    )
