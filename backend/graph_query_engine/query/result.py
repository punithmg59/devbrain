"""
Result Specification AST Models.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ResultProjection(BaseModel):
    """Field selection and transformation specification."""
    model_config = ConfigDict(frozen=True)

    projected_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Fields to return (empty means all)")
    alias_mapping: Dict[str, str] = Field(default_factory=dict, description="Field name aliases: {original: alias}")


class ResultOrdering(BaseModel):
    """Sort ordering specification."""
    model_config = ConfigDict(frozen=True)

    field_name: str = Field(..., description="Field name to order by")
    ascending: bool = Field(default=True, description="Order ascending if True")
    nulls_first: bool = Field(default=False, description="Place nulls first if True")


class ResultGrouping(BaseModel):
    """Group-by specification."""
    model_config = ConfigDict(frozen=True)

    group_fields: Tuple[str, ...] = Field(..., description="Group-by field tuple")


class ResultAggregation(BaseModel):
    """Result aggregation specification."""
    model_config = ConfigDict(frozen=True)

    function_name: str = Field(..., description="Aggregation function: COUNT, SUM, AVG, MIN, MAX")
    field_name: Optional[str] = Field(default=None, description="Target field name for aggregation")
    result_alias: str = Field(..., description="Output alias for aggregated value")


class ResultPagination(BaseModel):
    """Result pagination specification."""
    model_config = ConfigDict(frozen=True)

    offset: int = Field(default=0, ge=0, description="Offset starting index")
    limit: Optional[int] = Field(default=None, ge=0, description="Max items limit")


class ResultDeduplication(BaseModel):
    """Result deduplication specification."""
    model_config = ConfigDict(frozen=True)

    distinct: bool = Field(default=False, description="Enable distinct deduplication if True")
    distinct_on_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Fields to deduplicate on")


class FormattingMetadata(BaseModel):
    """Output formatting preferences."""
    model_config = ConfigDict(frozen=True)

    format_type: str = Field(default="JSON", description="Format type: JSON, GRAPH_JSON, TABLE, SUMMARY")
    include_statistics: bool = Field(default=False, description="Include execution statistics in payload")
    pretty_print: bool = Field(default=False, description="Enable pretty-printed output")


class ResultSpecification(BaseModel):
    """
    Immutable container representing desired query result shaping, ordering, and formatting.
    """
    model_config = ConfigDict(frozen=True)

    projection: ResultProjection = Field(default_factory=ResultProjection, description="Projection spec")
    orderings: Tuple[ResultOrdering, ...] = Field(default_factory=tuple, description="Ordering specs tuple")
    grouping: Optional[ResultGrouping] = Field(default=None, description="Grouping spec")
    aggregations: Tuple[ResultAggregation, ...] = Field(default_factory=tuple, description="Aggregation specs tuple")
    pagination: ResultPagination = Field(default_factory=ResultPagination, description="Pagination spec")
    deduplication: ResultDeduplication = Field(default_factory=ResultDeduplication, description="Deduplication spec")
    formatting: FormattingMetadata = Field(default_factory=FormattingMetadata, description="Formatting metadata")


__all__ = [
    "ResultProjection",
    "ResultOrdering",
    "ResultGrouping",
    "ResultAggregation",
    "ResultPagination",
    "ResultDeduplication",
    "FormattingMetadata",
    "ResultSpecification",
]
