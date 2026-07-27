"""
Immutable Logical Operator Nodes.

Logical operators represent the logical operations ("what work needs to be performed")
without specifying physical execution strategies, index selections, or graph algorithms.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.expressions import QueryExpression
from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.query.references import EntityReference
from graph_query_engine.query.traversal import TraversalRequest


class LogicalOperator(BaseModel):
    """
    Base immutable logical operator AST model.
    """
    model_config = ConfigDict(frozen=True)

    operator_id: str = Field(..., description="Unique logical operator instance ID")
    operator_name: str = Field(..., description="Logical operator classification string")
    output_schema: Tuple[str, ...] = Field(default_factory=tuple, description="Expected output attribute names")

    def accept(self, visitor: Any) -> Any:
        """Visitor pattern entrypoint dispatching to visitor.visit_operator(self)."""
        return visitor.visit_operator(self)

    def validate_operator(self) -> List[str]:
        """Validates operator configuration returning a list of validation error strings."""
        errors: List[str] = []
        if not self.operator_id:
            errors.append("LogicalOperator must have a non-empty operator_id.")
        if not self.operator_name:
            errors.append("LogicalOperator must have a non-empty operator_name.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes logical operator into a dictionary representation."""
        return self.model_dump(mode="python")


class LogicalLookupOperator(LogicalOperator):
    """Logical entity or symbol lookup operation."""
    operator_name: str = Field(default="LOGICAL_LOOKUP", description="Discriminator for lookup operator")
    target_reference: EntityReference = Field(..., description="Target entity reference model")


class LogicalExpandOperator(LogicalOperator):
    """Logical graph relationship expansion operation."""
    operator_name: str = Field(default="LOGICAL_EXPAND", description="Discriminator for expand operator")
    traversal_request: TraversalRequest = Field(default_factory=TraversalRequest, description="Traversal specification")


class LogicalFilterOperator(LogicalOperator):
    """Logical predicate filtering operation."""
    operator_name: str = Field(default="LOGICAL_FILTER", description="Discriminator for filter operator")
    predicate: QueryPredicate = Field(..., description="Filter predicate node")


class LogicalProjectionOperator(LogicalOperator):
    """Logical attribute projection operation."""
    operator_name: str = Field(default="LOGICAL_PROJECTION", description="Discriminator for projection operator")
    projected_fields: Tuple[str, ...] = Field(..., description="Projected attribute names")
    alias_mapping: Dict[str, str] = Field(default_factory=dict, description="Field name aliases")


class LogicalAggregateOperator(LogicalOperator):
    """Logical aggregation operation (COUNT, SUM, AVG, MIN, MAX)."""
    operator_name: str = Field(default="LOGICAL_AGGREGATE", description="Discriminator for aggregate operator")
    function_name: str = Field(..., description="Aggregate function name")
    expression: Optional[QueryExpression] = Field(default=None, description="Aggregated expression")
    result_alias: str = Field(..., description="Output attribute alias for aggregate result")


class LogicalGroupingOperator(LogicalOperator):
    """Logical group-by operation."""
    operator_name: str = Field(default="LOGICAL_GROUPING", description="Discriminator for grouping operator")
    group_keys: Tuple[str, ...] = Field(..., description="Attributes to group by")


class LogicalSortingOperator(LogicalOperator):
    """Logical sorting / ordering operation."""
    operator_name: str = Field(default="LOGICAL_SORTING", description="Discriminator for sorting operator")
    field_name: str = Field(..., description="Sort attribute name")
    ascending: bool = Field(default=True, description="Sort direction ascending if True")


class LogicalDeduplicationOperator(LogicalOperator):
    """Logical distinct deduplication operation."""
    operator_name: str = Field(default="LOGICAL_DEDUPLICATION", description="Discriminator for deduplication operator")
    distinct_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Attributes to deduplicate on")


class LogicalJoinOperator(LogicalOperator):
    """Logical join operation combining two logical plan branches."""
    operator_name: str = Field(default="LOGICAL_JOIN", description="Discriminator for join operator")
    join_type: str = Field(default="INNER", description="Join type: INNER, LEFT, RIGHT, FULL")
    on_predicate: QueryPredicate = Field(..., description="Join condition predicate")


class LogicalLimitOperator(LogicalOperator):
    """Logical pagination limit and offset operation."""
    operator_name: str = Field(default="LOGICAL_LIMIT", description="Discriminator for limit operator")
    limit: int = Field(..., ge=0, description="Max items to emit")
    offset: int = Field(default=0, ge=0, description="Items to skip")


__all__ = [
    "LogicalOperator",
    "LogicalLookupOperator",
    "LogicalExpandOperator",
    "LogicalFilterOperator",
    "LogicalProjectionOperator",
    "LogicalAggregateOperator",
    "LogicalGroupingOperator",
    "LogicalSortingOperator",
    "LogicalDeduplicationOperator",
    "LogicalJoinOperator",
    "LogicalLimitOperator",
]
