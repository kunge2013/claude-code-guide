"""
LangChain tools for Resume Template Agent
Provides tools to query the resume template knowledge base with multiple search strategies
"""
import pandas as pd
import os
from typing import Optional
from langchain_core.tools import tool

from .config import Config
from .strategies import StrategyFactory


# Load the knowledge base once at module import
_knowledge_base: Optional[pd.DataFrame] = None


def load_knowledge_base() -> pd.DataFrame:
    """Load the Excel knowledge base file"""
    global _knowledge_base

    if _knowledge_base is not None:
        return _knowledge_base

    if not os.path.exists(Config.EXCEL_FILE_PATH):
        raise FileNotFoundError(f"Knowledge base file not found: {Config.EXCEL_FILE_PATH}")

    _knowledge_base = pd.read_excel(Config.EXCEL_FILE_PATH)
    return _knowledge_base


def _format_search_result(result) -> str:
    """
    Format SearchResult into a human-readable string.

    Args:
        result: SearchResult object from a search strategy

    Returns:
        Formatted string with template names and download links
    """
    if not result.matches:
        # No matches - return available templates
        df = load_knowledge_base()
        available = "\n".join([f"- {template}" for template in df['问题'].tolist()])

        return f"""抱歉，未找到"{result.query}"相关的简历模板。

目前可用的简历模板包括：
{available}

请尝试以上关键词之一。"""

    # Filter out suggestions (items without download links)
    valid_matches = [m for m in result.matches if m.download_link]

    if not valid_matches:
        # Only suggestions available
        df = load_knowledge_base()
        available = "\n".join([f"- {template}" for template in df['问题'].tolist()])

        return f"""抱歉，未找到"{result.query}"相关的简历模板。

目前可用的简历模板包括：
{available}

请尝试以上关键词之一。"""

    # Format valid matches
    output_lines = []
    for match in valid_matches:
        output_lines.append(f"""**模板名称**: {match.template_name}
**下载地址**: {match.download_link}""")

    return "\n\n".join(output_lines)


@tool
def search_resume_template(query: str, mode: str = None) -> str:
    """
    Search for resume templates in the knowledge base.

    Supports three search modes:
    - fuzzy: Fuzzy string matching (fast, works well for exact keywords)
    - vector: Semantic vector search (better for natural language queries)
    - hybrid: Combined approach (best accuracy)

    Args:
        query: The search query for resume template type (e.g., "人事行政", "大学生", "互联网")
        mode: Optional search mode override ("fuzzy", "vector", or "hybrid").
              If not specified, uses the SEARCH_MODE config setting.

    Returns:
        Formatted string with template name and download link

    Examples:
        >>> search_resume_template("人事行政简历模板")
        "**模板名称**: 人事行政简历模板\\n**下载地址**: https://pan.baidu.com/s/..."

        >>> search_resume_template("通用简历", mode="vector")
        "**模板名称**: 通用简历模板\\n**下载地址**: https://pan.baidu.com/s/..."
    """
    try:
        # Get search mode from config or parameter
        search_mode = mode or Config.SEARCH_MODE

        # Create strategy and execute search
        config = Config()
        strategy = StrategyFactory.create_strategy(search_mode, config)
        result = strategy.search(query)

        # Format and return results
        return _format_search_result(result)

    except Exception as e:
        return f"查询简历模板时出错: {str(e)}"


@tool
def list_all_templates() -> str:
    """
    List all available resume templates in the knowledge base.

    Returns:
        Formatted string listing all available templates

    Examples:
        >>> list_all_templates()
        "可用的简历模板：\\n1. 人事行政简历模板\\n2. 互联网职位模板..."
    """
    try:
        df = load_knowledge_base()
        templates = df['问题'].tolist()

        result = "可用的简历模板：\n"
        for i, template in enumerate(templates, 1):
            result += f"{i}. {template}\n"

        return result.strip()

    except Exception as e:
        return f"获取模板列表时出错: {str(e)}"


@tool
def get_template_by_exact_name(template_name: str) -> str:
    """
    Get a resume template by exact name match.

    Args:
        template_name: The exact name of the template (e.g., "人事行政简历模板")

    Returns:
        Formatted string with template name and download link, or error message if not found

    Examples:
        >>> get_template_by_exact_name("人事行政简历模板")
        "**模板名称**: 人事行政简历模板\\n**下载地址**: https://pan.baidu.com/s/..."
    """
    try:
        df = load_knowledge_base()

        # Exact match
        result = df[df['问题'] == template_name]

        if not result.empty:
            download_link = result.iloc[0]['答案']
            return f"""**模板名称**: {template_name}
**下载地址**: {download_link}"""

        # Not found - suggest similar templates
        all_templates = df['问题'].tolist()

        return f"""未找到名为"{template_name}"的简历模板。

请使用 list_all_templates 查看所有可用模板，或使用 search_resume_template 进行模糊搜索。"""

    except Exception as e:
        return f"获取模板时出错: {str(e)}"


# Export all tools
__all__ = [
    "search_resume_template",
    "list_all_templates",
    "get_template_by_exact_name",
]
