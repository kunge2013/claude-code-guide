"""
LangChain tools for Resume Template Agent
Provides tools to query the Excel-based resume template knowledge base
"""
import pandas as pd
import os
from typing import Optional, List, Dict
from langchain_core.tools import tool
from thefuzz import fuzz

from .config import Config


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


@tool
def search_resume_template(query: str) -> str:
    """
    Search for resume templates in the knowledge base.

    Args:
        query: The search query for resume template type (e.g., "人事行政", "大学生", "互联网")

    Returns:
        Formatted string with template name and download link

    Examples:
        >>> search_resume_template("人事行政简历模板")
        "**模板名称**: 人事行政简历模板\\n**下载地址**: https://pan.baidu.com/s/..."

        >>> search_resume_template("通用简历")
        "**模板名称**: 通用简历模板\\n**下载地址**: https://pan.baidu.com/s/..."
    """
    try:
        df = load_knowledge_base()

        # Get all available templates
        all_templates = df['问题'].tolist()

        # Perform fuzzy matching
        best_match = None
        best_score = 0

        for template in all_templates:
            # Calculate similarity score
            score = fuzz.partial_ratio(query, template)

            # Bonus for exact keyword matches
            for keyword in query.split():
                if keyword in template:
                    score += 20

            if score > best_score:
                best_score = score
                best_match = template

        # Threshold for matching (minimum 60% similarity)
        THRESHOLD = 60

        if best_match and best_score >= THRESHOLD:
            # Find the corresponding download link
            result_row = df[df['问题'] == best_match].iloc[0]
            download_link = result_row['答案']

            return f"""**模板名称**: {best_match}
**下载地址**: {download_link}"""

        # No match found - return available templates
        available = "\n".join([f"- {template}" for template in all_templates])

        return f"""抱歉，未找到"{query}"相关的简历模板。

目前可用的简历模板包括：
{available}

请尝试以上关键词之一。"""

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
