"""
Resume Template Agent Package
A LangChain-based agent for querying resume template knowledge base
"""
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Set HF_ENDPOINT BEFORE any other imports that might use FlagEmbedding
# This is critical for Chinese users to avoid HuggingFace network issues
hf_endpoint = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
os.environ["HF_ENDPOINT"] = hf_endpoint

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
