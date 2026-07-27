"""
Physical Plan Representation Models.

Immutable tree structure representing selected physical operators and execution strategies.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.cost import CostEstimate
from graph_query_engine.physical.diagnostics import PhysicalPlannerDiagnosticItem
from graph_query_engine.physical.operators import PhysicalOperator
from graph_query_engine.physical.version import PhysicalPlanVersion
from graph_query_engine.types import QueryId


class PhysicalPlanNode(BaseModel):
    """
    Composite tree node wrapping a physical execution operator and child physical input nodes.
    """
    model_config = ConfigDict(frozen=True)

    node_id: str = Field(..., description="Unique physical plan tree node ID")
    operator: PhysicalOperator = Field(..., description="Physical operator content")
    children: Tuple["PhysicalPlanNode", ...] = Field(default_factory=tuple, description="Child physical plan input nodes")

    def accept(self, visitor: Any) -> Any:
        """Visits this physical plan node."""
        return visitor.visit_physical_plan_node(self)

    def calculate_node_count(self) -> int:
        """Calculates total node count in subtree."""
        return 1 + sum(child.calculate_node_count() for child in self.children)

    def calculate_depth(self) -> int:
        """Calculates maximum tree depth."""
        if not self.children:
            return 1
        return 1 + max(child.calculate_depth() for child in self.children)


class PhysicalPlanMetadata(BaseModel):
    """
    Immutable metadata container for a PhysicalPlan.
    """
    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    node_count: int = Field(default=1, ge=1, description="Total physical plan tree node count")
    tree_depth: int = Field(default=1, ge=1, description="Physical plan tree depth")
    execution_strategy_name: str = Field(default="DEFAULT_PHYSICAL_STRATEGY", description="Summary strategy name")
    strategy_rationales: Tuple[str, ...] = Field(default_factory=tuple, description="Rationale strings for strategy selections")


class PhysicalPlan(BaseModel):
    """
    Canonical immutable PhysicalPlan output model produced by PhysicalPlanner.
    """
    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(
        default_factory=lambda: f"pplan_{uuid.uuid4().hex[:12]}",
        description="Unique PhysicalPlan identifier string",
    )
    logical_plan_id: str = Field(..., description="Associated input LogicalPlan plan_id")
    query_id: QueryId = Field(..., description="Associated source QueryId")
    version: PhysicalPlanVersion = Field(default_factory=PhysicalPlanVersion, description="Physical plan version model")
    metadata: PhysicalPlanMetadata = Field(default_factory=PhysicalPlanMetadata, description="Plan metadata container")
    total_cost_estimate: CostEstimate = Field(default_factory=CostEstimate, description="Total estimated cost")
    root_node: PhysicalPlanNode = Field(..., description="Root node of the physical operator tree")
    diagnostics: Tuple[PhysicalPlannerDiagnosticItem, ...] = Field(default_factory=tuple, description="Physical planner diagnostics log")

    def accept(self, visitor: Any) -> Any:
        """Visits this PhysicalPlan container."""
        return visitor.visit_physical_plan(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PhysicalPlan to python dict."""
        return self.model_dump(mode="python")


__all__ = [
    "PhysicalPlanNode",
    "PhysicalPlanMetadata",
    "PhysicalPlan",
]
