"""
Structural Query Operator AST Nodes.

Pure structural representation of engineering query operators.
DOES NOT perform planning, optimization, index lookup, or execution.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.expressions import QueryExpression
from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.query.references import EntityReference
from graph_query_engine.query.traversal import TraversalRequest


class QueryOperator(BaseModel):
    """
    Base immutable query operator AST node.
    """
    model_config = ConfigDict(frozen=True)

    operator_type: str = Field(..., description="Query operator type discriminator string")
    alias: Optional[str] = Field(default=None, description="Optional result binding alias string")


class LookupOperator(QueryOperator):
    """Direct entity or node lookup operator."""
    operator_type: str = Field(default="LOOKUP", description="Discriminator for lookup operator")
    target_reference: EntityReference = Field(..., description="Target entity reference to lookup")


class ExpandOperator(QueryOperator):
    """1-hop or n-hop relationship expansion operator."""
    operator_type: str = Field(default="EXPAND", description="Discriminator for expand operator")
    source: EntityReference = Field(..., description="Source entity reference to expand from")
    traversal_request: TraversalRequest = Field(default_factory=TraversalRequest, description="Traversal specification")


class ImpactOperator(QueryOperator):
    """Downstream or upstream change impact analysis operator."""
    operator_type: str = Field(default="IMPACT", description="Discriminator for impact operator")
    target_reference: EntityReference = Field(..., description="Target entity reference under impact analysis")
    max_depth: int = Field(default=5, ge=1, description="Maximum impact search depth")


class ReachabilityOperator(QueryOperator):
    """Path reachability check operator between source and target entities."""
    operator_type: str = Field(default="REACHABILITY", description="Discriminator for reachability operator")
    source_reference: EntityReference = Field(..., description="Source starting entity reference")
    target_reference: EntityReference = Field(..., description="Target destination entity reference")
    max_depth: Optional[int] = Field(default=None, description="Optional max depth constraint")


class UsageSearchOperator(QueryOperator):
    """Symbol or entity call/usage reference search operator."""
    operator_type: str = Field(default="USAGE_SEARCH", description="Discriminator for usage search operator")
    target_reference: EntityReference = Field(..., description="Target entity reference whose usages are searched")
    include_indirect: bool = Field(default=False, description="Include indirect/transitive usages if True")


class HierarchyOperator(QueryOperator):
    """Inheritance or type hierarchy operator (subtypes, supertypes)."""
    operator_type: str = Field(default="HIERARCHY", description="Discriminator for hierarchy operator")
    target_reference: EntityReference = Field(..., description="Target entity reference")
    direction: str = Field(default="SUBTYPES", description="Hierarchy direction: SUBTYPES, SUPERTYPES, BOTH")


class PathOperator(QueryOperator):
    """Shortest or all-paths query operator between entity pairs."""
    operator_type: str = Field(default="PATH", description="Discriminator for path operator")
    source_reference: EntityReference = Field(..., description="Source starting entity reference")
    target_reference: EntityReference = Field(..., description="Target destination entity reference")
    path_type: str = Field(default="SHORTEST", description="Path type: SHORTEST, ALL, ACYCLIC")


class AggregateOperator(QueryOperator):
    """Aggregation operator (COUNT, SUM, AVG, MIN, MAX)."""
    operator_type: str = Field(default="AGGREGATE", description="Discriminator for aggregate operator")
    function_name: str = Field(..., description="Aggregate function: COUNT, SUM, AVG, MIN, MAX")
    expression: Optional[QueryExpression] = Field(default=None, description="Aggregated expression")


class ProjectionOperator(QueryOperator):
    """Field or attribute projection operator."""
    operator_type: str = Field(default="PROJECTION", description="Discriminator for projection operator")
    fields: Tuple[str, ...] = Field(..., description="Tuple of projected field names")


class GroupingOperator(QueryOperator):
    """Group-by operator for query results."""
    operator_type: str = Field(default="GROUPING", description="Discriminator for grouping operator")
    group_keys: Tuple[str, ...] = Field(..., description="Tuple of field names to group by")


class SortingOperator(QueryOperator):
    """Sorting / Order-By operator."""
    operator_type: str = Field(default="SORTING", description="Discriminator for sorting operator")
    field_name: str = Field(..., description="Field name to sort by")
    ascending: bool = Field(default=True, description="Sort direction ascending if True")


class DeduplicationOperator(QueryOperator):
    """Distinct / Deduplication operator."""
    operator_type: str = Field(default="DEDUPLICATION", description="Discriminator for deduplication operator")
    target_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Fields to deduplicate on (all if empty)")


class LimitOperator(QueryOperator):
    """Result pagination limit and offset operator."""
    operator_type: str = Field(default="LIMIT", description="Discriminator for limit operator")
    limit: int = Field(..., ge=0, description="Maximum number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class FilterOperator(QueryOperator):
    """Predicate filtering operator."""
    operator_type: str = Field(default="FILTER", description="Discriminator for filter operator")
    predicate: QueryPredicate = Field(..., description="Filter predicate AST node")


class JoinOperator(QueryOperator):
    """Logical join operator combining two query operations."""
    operator_type: str = Field(default="JOIN", description="Discriminator for join operator")
    left_alias: str = Field(..., description="Left side operator alias")
    right_alias: str = Field(..., description="Right side operator alias")
    join_type: str = Field(default="INNER", description="Join type: INNER, LEFT, RIGHT, FULL")
    on_predicate: QueryPredicate = Field(..., description="Join condition predicate")


__all__ = [
    "QueryOperator",
    "LookupOperator",
    "ExpandOperator",
    "ImpactOperator",
    "ReachabilityOperator",
    "UsageSearchOperator",
    "HierarchyOperator",
    "PathOperator",
    "AggregateOperator",
    "ProjectionOperator",
    "GroupingOperator",
    "SortingOperator",
    "DeduplicationOperator",
    "LimitOperator",
    "FilterOperator",
    "JoinOperator",
]
