"""
LogicalPlan Models and Tree Container.

Completely independent of physical execution strategies, index selection, or graph storage.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.logical.diagnostics import LogicalPlannerDiagnosticItem
from graph_query_engine.logical.operators import LogicalOperator
from graph_query_engine.logical.version import LogicalPlanVersion
from graph_query_engine.types import QueryId


class LogicalPlanNode(BaseModel):
    """
    Composite tree node wrapping a LogicalOperator and its child input nodes.
    """
    model_config = ConfigDict(frozen=True)

    node_id: str = Field(..., description="Unique logical plan node ID")
    operator: LogicalOperator = Field(..., description="Wrapped logical operator instance")
    children: Tuple["LogicalPlanNode", ...] = Field(default_factory=tuple, description="Child input logical plan nodes")

    def accept(self, visitor: Any) -> Any:
        """Visitor pattern entrypoint dispatching to visitor.visit_plan_node(self)."""
        return visitor.visit_plan_node(self)

    def validate_tree(self) -> List[str]:
        """Validates operator and child tree structure recursively."""
        errors: List[str] = self.operator.validate_operator()
        if not self.node_id:
            errors.append("LogicalPlanNode must have a non-empty node_id.")
        for child in self.children:
            errors.extend(child.validate_tree())
        return errors

    def calculate_depth(self) -> int:
        """Calculates maximum depth of the logical operator tree."""
        if not self.children:
            return 1
        return 1 + max(child.calculate_depth() for child in self.children)

    def calculate_node_count(self) -> int:
        """Calculates total count of logical nodes in the tree."""
        return 1 + sum(child.calculate_node_count() for child in self.children)


class LogicalPlanMetadata(BaseModel):
    """
    Immutable metadata describing a generated LogicalPlan.
    """
    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    node_count: int = Field(default=1, ge=1, description="Total node count in plan tree")
    tree_depth: int = Field(default=1, ge=1, description="Maximum tree depth")
    lowering_rules_applied: Tuple[str, ...] = Field(default_factory=tuple, description="Lowering rule IDs applied during plan construction")


class LogicalPlanStatistics(BaseModel):
    """
    Placeholder statistics model for future Cost Model consumption.
    Contains NO actual physical estimates during Step 4.3.
    """
    model_config = ConfigDict(frozen=True)

    estimated_cardinality: Optional[float] = Field(default=None, description="Placeholder estimated cardinality")
    estimated_row_count: Optional[float] = Field(default=None, description="Placeholder estimated row count")
    estimated_bytes: Optional[float] = Field(default=None, description="Placeholder estimated byte size")


class LogicalPlan(BaseModel):
    """
    Canonical immutable Logical Plan produced by LogicalPlanner.

    Represents the logical query execution graph independently of physical execution engines.
    """
    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(
        default_factory=lambda: f"lplan_{uuid.uuid4().hex[:12]}",
        description="Unique LogicalPlan identifier string",
    )
    query_id: QueryId = Field(..., description="Associated EngineeringQuery query_id")
    version: LogicalPlanVersion = Field(default_factory=LogicalPlanVersion, description="Plan schema version")
    metadata: LogicalPlanMetadata = Field(default_factory=LogicalPlanMetadata, description="Plan metadata")
    statistics: LogicalPlanStatistics = Field(default_factory=LogicalPlanStatistics, description="Statistics placeholder model")
    root_node: LogicalPlanNode = Field(..., description="Root node of the logical operator tree")
    diagnostics: Tuple[LogicalPlannerDiagnosticItem, ...] = Field(default_factory=tuple, description="Planner diagnostics log")

    def accept(self, visitor: Any) -> Any:
        """Dispatches visitor to LogicalPlan root."""
        return visitor.visit_plan(self)

    def validate_plan(self) -> List[str]:
        """Validates entire logical plan tree."""
        errors: List[str] = []
        if not str(self.query_id):
            errors.append("LogicalPlan query_id cannot be empty.")
        errors.extend(self.root_node.validate_tree())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes LogicalPlan to python dictionary."""
        return self.model_dump(mode="python")


__all__ = [
    "LogicalPlanNode",
    "LogicalPlanMetadata",
    "LogicalPlanStatistics",
    "LogicalPlan",
]
