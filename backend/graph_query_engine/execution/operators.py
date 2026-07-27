"""
Immutable Execution Operator Infrastructure.

Defines runtime execution instructions and operator definitions.
100% Immutable (Pydantic frozen models). Pure representation, ZERO execution.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.cost import CostEstimate
from graph_query_engine.physical.operators import PhysicalOperator
from graph_query_engine.query.predicates import QueryPredicate


class ExecutionOperator(BaseModel):
    """
    Abstract base class for all execution runtime operators.
    """
    model_config = ConfigDict(frozen=True)

    execution_operator_id: str = Field(..., description="Unique execution operator instance ID")
    operator_name: str = Field(..., description="Execution operator classification name")
    output_schema: Tuple[str, ...] = Field(default_factory=tuple, description="Output schema attribute names")
    physical_operator_ref: Optional[str] = Field(default=None, description="Source PhysicalOperator operator_id reference")
    estimated_cost: CostEstimate = Field(default_factory=CostEstimate, description="Associated CostEstimate")

    def accept(self, visitor: Any) -> Any:
        """Visits this execution operator."""
        return visitor.visit_execution_operator(self)

    def validate_operator(self) -> List[str]:
        """Validates operator configuration invariants. Returns list of error messages."""
        errors = []
        if not self.execution_operator_id:
            errors.append("ExecutionOperator execution_operator_id cannot be empty.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes operator to python dict."""
        return self.model_dump(mode="python")


class IndexLookupExecutionOperator(ExecutionOperator):
    """Execution operator for index lookup scans."""
    operator_name: str = "INDEX_LOOKUP_EXEC"
    index_name: str = Field(default="PRIMARY_INDEX", description="Index name")


class SequentialLookupExecutionOperator(ExecutionOperator):
    """Execution operator for sequential table/node scans."""
    operator_name: str = "SEQUENTIAL_LOOKUP_EXEC"


class ExpandExecutionOperator(ExecutionOperator):
    """Execution operator for graph expansion traversal."""
    operator_name: str = "EXPAND_EXEC"
    traversal_algorithm: str = Field(default="BFS", description="BFS, DFS, or BIDIRECTIONAL")


class FilterExecutionOperator(ExecutionOperator):
    """Execution operator for predicate filter evaluation."""
    operator_name: str = "FILTER_EXEC"
    predicate: Optional[QueryPredicate] = Field(default=None, description="Filter predicate")


class ProjectionExecutionOperator(ExecutionOperator):
    """Execution operator for attribute field projection."""
    operator_name: str = "PROJECTION_EXEC"
    projected_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Projected fields")


class AggregationExecutionOperator(ExecutionOperator):
    """Execution operator for streaming/hash aggregation."""
    operator_name: str = "AGGREGATION_EXEC"
    function_name: str = Field(default="COUNT", description="Aggregation function name")
    result_alias: str = Field(default="agg_val", description="Result attribute alias")


class SortingExecutionOperator(ExecutionOperator):
    """Execution operator for tuple sorting."""
    operator_name: str = "SORTING_EXEC"
    field_name: str = Field(..., description="Sorting field attribute")
    ascending: bool = Field(default=True, description="Ascending order flag")


class DeduplicationExecutionOperator(ExecutionOperator):
    """Execution operator for distinct deduplication."""
    operator_name: str = "DEDUPLICATION_EXEC"
    distinct_fields: Tuple[str, ...] = Field(default_factory=tuple, description="Distinct fields")


class HashJoinExecutionOperator(ExecutionOperator):
    """Execution operator for hash join evaluation."""
    operator_name: str = "HASH_JOIN_EXEC"
    join_type: str = Field(default="INNER", description="Join type")


class MergeJoinExecutionOperator(ExecutionOperator):
    """Execution operator for sorted merge join evaluation."""
    operator_name: str = "MERGE_JOIN_EXEC"
    join_type: str = Field(default="INNER", description="Join type")


class NestedLoopExecutionOperator(ExecutionOperator):
    """Execution operator for nested loop join evaluation."""
    operator_name: str = "NESTED_LOOP_EXEC"
    join_type: str = Field(default="INNER", description="Join type")


class LimitExecutionOperator(ExecutionOperator):
    """Execution operator for pagination limit and offset."""
    operator_name: str = "LIMIT_EXEC"
    limit: int = Field(..., ge=0, description="Limit count")
    offset: int = Field(default=0, ge=0, description="Offset count")


__all__ = [
    "ExecutionOperator",
    "IndexLookupExecutionOperator",
    "SequentialLookupExecutionOperator",
    "ExpandExecutionOperator",
    "FilterExecutionOperator",
    "ProjectionExecutionOperator",
    "AggregationExecutionOperator",
    "SortingExecutionOperator",
    "DeduplicationExecutionOperator",
    "HashJoinExecutionOperator",
    "MergeJoinExecutionOperator",
    "NestedLoopExecutionOperator",
    "LimitExecutionOperator",
]
