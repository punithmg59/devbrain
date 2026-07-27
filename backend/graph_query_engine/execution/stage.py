"""
Execution Stage Infrastructure.

Independent, dependency-aware executable stages partitioning a PhysicalPlan pipeline.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.cost import CostEstimate
from graph_query_engine.execution.operators import ExecutionOperator


class ExecutionStage(BaseModel):
    """
    Immutable independently executable stage container.
    """
    model_config = ConfigDict(frozen=True)

    stage_id: str = Field(..., description="Unique execution stage ID string")
    stage_name: str = Field(..., description="Execution stage classification name")
    stage_type: str = Field(..., description="Stage type: LOOKUP, FILTER, EXPANSION, AGGREGATION, SORTING, PROJECTION, JOIN, DEDUPLICATION, LIMIT")
    operators: Tuple[ExecutionOperator, ...] = Field(default_factory=tuple, description="Tuple of execution operators contained in this stage")
    dependencies: Tuple[str, ...] = Field(default_factory=tuple, description="Tuple of stage_ids that must complete before this stage executes")
    estimated_stage_cost: CostEstimate = Field(default_factory=CostEstimate, description="Estimated execution cost for this stage")

    def accept(self, visitor: Any) -> Any:
        """Visits this execution stage."""
        return visitor.visit_execution_stage(self)

    def validate_stage(self) -> List[str]:
        """Validates stage configuration invariants. Returns list of error messages."""
        errors = []
        if not self.stage_id:
            errors.append("ExecutionStage stage_id cannot be empty.")
        if not self.operators:
            errors.append(f"ExecutionStage '{self.stage_id}' must contain at least one ExecutionOperator.")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes stage to python dict."""
        return self.model_dump(mode="python")


__all__ = ["ExecutionStage"]
