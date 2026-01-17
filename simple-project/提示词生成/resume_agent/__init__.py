"""
Resume Template Agent Package
A LangChain-based agent for querying resume template knowledge base
"""
from .agent import ResumeTemplateAgent
from .config import Config
from .tools import search_resume_template, list_all_templates, get_template_by_exact_name

__version__ = "0.1.0"

__all__ = [
    "ResumeTemplateAgent",
    "Config",
    "search_resume_template",
    "list_all_templates",
    "get_template_by_exact_name",
]
