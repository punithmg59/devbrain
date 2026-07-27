"""
Immutable Physical Operator Infrastructure.

Defines execution strategies, algorithm selections, and physical plan nodes.
100% Immutable (Pydantic frozen models). Pure representation, ZERO execution.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.cost import CostEstimate
from graph_query_engine.query.predicates import QueryPredicate
from graph_query_engine.query.references import EntityReference, SymbolReference
from graph_query_engine.query.traversal import TraversalRequest


class PhysicalOperator(BaseModel):
    """
    Abstract base class for all physical execution operators.
    """
    model_config = ConfigDict(frozen=True)

    operator_id: str = Field(..., description="Unique physical operator instance ID")
    operator_name: str = Field(..., description="Physical operator classification name")
    output_schema: Tuple[str, ...] = Field(default_factory=tuple, description="Output schema attribute names")
    estimated_cost: CostEstimate = Field(default_factory=CostEstimate, description="Associated CostEstimate for this physical operator")

    def accept(self, visitor: Any) -> Any:
        """Visits this physical operator."""
        return visitor.visit_physical_operator(self)

    def validate_operator(self) -> List[str]:
        """Validates operator configuration invariants. Returns list of error messages."""
        errors = []
        if not self.operator_id:
            errors.append("PhysicalOperator operator_id cannot be empty.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes operator to python dict."""
        return self.model_dump(mode="python")


class IndexLookupPhysicalOperator(PhysicalOperator):
    """Physical operator using B-Tree / CSR / Hash index lookup strategy."""
    operator_name: str = "INDEX_LOOKUP"
    index_name: str = Field(default="PRIMARY_INDEX", description="Selected index name")
    target_reference: Optional[EntityReference] = Field(default=None, description="Target entity/symbol reference")


class SequentialLookupPhysicalOperator(PhysicalOperator):
    """Physical operator using sequential scan fallback strategy."""
    operator_name: str = "SEQUENTIAL_LOOKUP"
    target_reference: Optional[EntityReference] = Field(default=None, description="Target entity/symbol reference")


class BreadthExpandPhysicalOperator(PhysicalOperator):
    """Physical graph expansion using Breadth-First Search (BFS) strategy."""
    operator_name: str = "BREADTH_EXPAND"
    traversal_request: TraversalRequest = Field(default_factory=TraversalRequest, description="Traversal request spec")


class DepthExpandPhysicalOperator(PhysicalOperator):
    """Physical graph expansion using Depth-First Search (DFS) strategy."""
    operator_name: str = "DEPTH_EXPAND"
    traversal_request: TraversalRequest = Field(default_factory=TraversalRequest, description="Traversal request spec")


class BidirectionalExpandPhysicalOperator(PhysicalOperator):
    """Physical graph expansion using Bidirectional search strategy."""
    operator_name: str = "BIDIRECTIONAL_EXPAND"
    traversal_request: TraversalRequest = Field(default_factory=TraversalRequest, description="Traversal request spec")


class PathExpandPhysicalOperator(PhysicalOperator):
    """Physical path search expansion operator."""
    operator_name: str = "PATH_EXPAND"
    max_path_length: int = Field(default=10, ge=1, description="Maximum path search length")


class HierarchyExpandPhysicalOperator(PhysicalOperator):
    """Physical symbol hierarchy expansion operator."""
    operator_name: str = "HIERARCHY_EXPAND"
    hierarchy_direction: str = Field(default="UPSTREAM", description="UPSTREAM or DOWNSTREAM")


class FilterPushdownPhysicalOperator(PhysicalOperator):
    """Physical operator performing pushed-down predicate filter evaluation."""
    operator_name: str = "FILTER_PUSHDOWN"
    predicate: Optional[QueryPredicate] = Field(default=None, description="Filter predicate")


class ProjectionPushdownPhysicalOperator(PhysicalOperator):
    """Physical operator performing pushed-down field projection."""
    operator_name: str = "PROJECTION_PUSHDOWN"
    projected_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Fields to project")


class HashJoinPhysicalOperator(PhysicalOperator):
    """Physical join using in-memory hash join algorithm."""
    operator_name: str = "HASH_JOIN"
    join_type: str = Field(default="INNER", description="Join type")
    on_predicate: Optional[QueryPredicate] = Field(default=None, description="Join condition predicate")


class NestedLoopJoinPhysicalOperator(PhysicalOperator):
    """Physical join using nested loop join algorithm."""
    operator_name: str = "NESTED_LOOP_JOIN"
    join_type: str = Field(default="INNER", description="Join type")
    on_predicate: Optional[QueryPredicate] = Field(default=None, description="Join condition predicate")


class MergeJoinPhysicalOperator(PhysicalOperator):
    """Physical join using sorted merge join algorithm."""
    operator_name: str = "MERGE_JOIN"
    join_type: str = Field(default="INNER", description="Join type")
    on_predicate: Optional[QueryPredicate] = Field(default=None, description="Join condition predicate")


class AggregationExecutionPhysicalOperator(PhysicalOperator):
    """Physical aggregation operator."""
    operator_name: str = "AGGREGATION_EXECUTION"
    function_name: str = Field(default="COUNT", description="Aggregation function name")
    result_alias: str = Field(default="agg_val", description="Output attribute alias")


class SortingExecutionPhysicalOperator(PhysicalOperator):
    """Physical sorting operator."""
    operator_name: str = "SORTING_EXECUTION"
    field_name: str = Field(..., description="Sorting field attribute")
    ascending: bool = Field(default=True, description="Ascending sort order")


class DeduplicationExecutionPhysicalOperator(PhysicalOperator):
    """Physical distinct deduplication operator."""
    operator_name: str = "DEDUPLICATION_EXECUTION"
    distinct_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Distinct attribute fields")


class LimitExecutionPhysicalOperator(PhysicalOperator):
    """Physical limit and offset pagination operator."""
    operator_name: str = "LIMIT_EXECUTION"
    limit: int = Field(..., ge=0, description="Limit count")
    offset: int = Field(default=0, ge=0, description="Offset count")


__all__ = [
    "PhysicalOperator",
    "IndexLookupPhysicalOperator",
    "SequentialLookupPhysicalOperator",
    "BreadthExpandPhysicalOperator",
    "DepthExpandPhysicalOperator",
    "BidirectionalExpandPhysicalOperator",
    "PathExpandPhysicalOperator",
    "HierarchyExpandPhysicalOperator",
    "FilterPushdownPhysicalOperator",
    "ProjectionPushdownPhysicalOperator",
    "HashJoinPhysicalOperator",
    "NestedLoopJoinPhysicalOperator",
    "MergeJoinPhysicalOperator",
    "AggregationExecutionPhysicalOperator",
    "SortingExecutionPhysicalOperator",
    "DeduplicationExecutionPhysicalOperator",
    "LimitExecutionPhysicalOperator",
]
