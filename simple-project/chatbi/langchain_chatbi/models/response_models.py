"""
Pydantic response models for structured LLM outputs.

These models define the expected output format for each agent using LangChain's
structured output capabilities.
"""

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Intent Classification Models
# ============================================================================


class IntentClassification(BaseModel):
    """
    Result of intent classification.

    Attributes:
        intent: The classified intent type
        reasoning: Explanation for the classification
        confidence: Confidence level (0.0-1.0)
    """

    intent: Literal["query", "greeting", "help", "clarification", "unknown"] = Field(
        description="The classified intent type"
    )
    reasoning: str = Field(description="Explanation for why this intent was chosen")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence level (0.0-1.0)"
    )


class AmbiguityDetection(BaseModel):
    """
    Result of ambiguity detection.

    Attributes:
        is_ambiguous: Whether the question is ambiguous
        ambiguity_type: Type of ambiguity detected
        clarification_question: Question to ask user for clarification
        options: Potential options to present to user
    """

    is_ambiguous: bool = Field(description="Whether the question is ambiguous")
    ambiguity_type: Literal[
        "completely_vague", "multiple_interpretations", "missing_critical_context", "none"
    ] = Field(description="The type of ambiguity detected")
    clarification_question: str = Field(
        default="", description="Question to ask user for clarification"
    )
    options: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Potential options to present to user (label + description)",
    )


# ============================================================================
# Chart Configuration Models
# ============================================================================


class ChartSpec(BaseModel):
    """
    Chart specification for visualization.

    Attributes:
        xField: Field for x-axis
        yField: Field for y-axis
        seriesField: Field for series/grouping
        angleField: Field for pie chart angles
        colorField: Field for color encoding
    """

    xField: Optional[str] = Field(default=None, description="Field for x-axis")
    yField: Optional[str] = Field(default=None, description="Field for y-axis")
    seriesField: Optional[str] = Field(
        default=None, description="Field for series/grouping"
    )
    angleField: Optional[str] = Field(
        default=None, description="Field for pie chart angles"
    )
    colorField: Optional[str] = Field(
        default=None, description="Field for color encoding"
    )


class ChartStyle(BaseModel):
    """
    Chart styling configuration.

    Attributes:
        fillColor: Fill color for bars/areas
        strokeColor: Border/line color
    """

    fillColor: Optional[str] = Field(default=None, description="Fill color (hex)")
    strokeColor: Optional[str] = Field(default=None, description="Stroke color (hex)")


class ChartConfig(BaseModel):
    """
    Complete chart configuration for visualization.

    Attributes:
        chartType: Type of chart to render
        title: Chart title
        description: Chart description
        spec: Chart field specifications
        style: Chart styling options
    """

    chartType: Literal[
        "bar", "line", "pie", "area", "scatter", "column", "table"
    ] = Field(description="Type of chart to generate")
    title: str = Field(description="Chart title")
    description: str = Field(description="Chart description explaining what it shows")
    spec: ChartSpec = Field(default_factory=ChartSpec, description="Chart field mappings")
    style: Optional[ChartStyle] = Field(
        default=None, description="Optional chart styling"
    )


# ============================================================================
# Diagnosis/Insights Models
# ============================================================================


class InsightSummary(BaseModel):
    """
    Data insights and key findings.

    Attributes:
        summary: Concise summary of the data (2-3 sentences)
        key_points: Key observations/trends (3-5 bullet points)
        confidence: Confidence in the insights (0.0-1.0)
    """

    summary: str = Field(
        description="Concise 2-3 sentence summary of the main findings"
    )
    key_points: List[str] = Field(
        description="3-5 key observations, trends, or patterns in the data"
    )
    confidence: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Confidence in insights (0.0-1.0)"
    )


# ============================================================================
# Schema Selection Models
# ============================================================================


class SelectedTable(BaseModel):
    """
    A selected table with its relevance reasoning.

    Attributes:
        name: Table name
        reason: Why this table is relevant
    """

    name: str = Field(description="Name of the selected table")
    reason: str = Field(description="Why this table is relevant to the question")


class SchemaSelection(BaseModel):
    """
    Result of schema selection.

    Attributes:
        tables: List of selected tables with reasoning
        excluded_tables: Tables that were explicitly excluded
    """

    tables: List[SelectedTable] = Field(
        description="Tables selected for answering the question"
    )
    excluded_tables: List[str] = Field(
        default_factory=list,
        description="Table names that are not relevant",
    )


# ============================================================================
# SQL Generation Models
# ============================================================================


class SQLGeneration(BaseModel):
    """
    Result of SQL generation.

    Attributes:
        sql: The generated SQL query
        explanation: Explanation of what the SQL does
        confidence: Confidence in the SQL (0.0-1.0)
    """

    sql: str = Field(description="The generated SQL query (PostgreSQL syntax)")
    explanation: str = Field(description="Explanation of what the SQL query does")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence in the SQL (0.0-1.0)"
    )


# ============================================================================
# Reasoning Models
# ============================================================================


class QueryReasoning(BaseModel):
    """
    Step-by-step query reasoning plan.

    Attributes:
        question_understanding: Understanding of the user's question
        required_data: What data is needed
        query_logic: The logical approach
        expected_output: What the result should show
    """

    question_understanding: str = Field(
        description="Understanding of what the user is asking"
    )
    required_data: str = Field(description="What data/tables are needed")
    query_logic: str = Field(description="The logical approach to answer the question")
    expected_output: str = Field(description="What the result should show")


# ============================================================================
# Answer Summarization Models
# ============================================================================


class AnswerSummary(BaseModel):
    """
    Natural language answer summary.

    Attributes:
        direct_answer: Direct answer to the question (1-2 sentences)
        key_findings: Key findings with numbers (3-5 bullet points)
        insights: Optional insights about trends/anomalies
        recommendations: Optional actionable recommendations
    """

    direct_answer: str = Field(
        description="Direct answer to the question in 1-2 sentences"
    )
    key_findings: List[str] = Field(
        description="3-5 key findings with specific numbers",
        min_length=1,
        max_length=7,
    )
    insights: Optional[List[str]] = Field(
        default=None, description="Optional insights about trends or anomalies"
    )
    recommendations: Optional[List[str]] = Field(
        default=None, description="Optional actionable recommendations"
    )
