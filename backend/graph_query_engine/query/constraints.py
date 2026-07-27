"""
Query Constraints and Budget AST Models.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class TimeBudgetConstraint(BaseModel):
    """Time budget limit constraint in seconds."""
    model_config = ConfigDict(frozen=True)

    max_seconds: float = Field(default=30.0, gt=0.0, description="Maximum execution timeout in seconds")


class MemoryBudgetConstraint(BaseModel):
    """Memory budget limit constraint in bytes."""
    model_config = ConfigDict(frozen=True)

    max_bytes: int = Field(default=104_857_600, gt=0, description="Maximum RAM bytes limit (100MB default)")


class NodeBudgetConstraint(BaseModel):
    """Maximum visited nodes budget constraint."""
    model_config = ConfigDict(frozen=True)

    max_nodes: int = Field(default=10_000, gt=0, description="Maximum nodes visited limit")


class TraversalBudgetConstraint(BaseModel):
    """Maximum graph edge steps budget constraint."""
    model_config = ConfigDict(frozen=True)

    max_edge_steps: int = Field(default=50_000, gt=0, description="Maximum graph edge steps limit")


class ResultLimitConstraint(BaseModel):
    """Result size limit constraint."""
    model_config = ConfigDict(frozen=True)

    max_results: int = Field(default=1_000, gt=0, description="Maximum returned items limit")


class ComplexityLimitConstraint(BaseModel):
    """Query AST complexity score limit constraint."""
    model_config = ConfigDict(frozen=True)

    max_complexity_score: float = Field(default=100.0, gt=0.0, description="Maximum allowed complexity score")


class PlannerConstraint(BaseModel):
    """Specific planner behavioral constraint."""
    model_config = ConfigDict(frozen=True)

    constraint_name: str = Field(..., description="Planner constraint rule name")
    value: Any = Field(..., description="Constraint configuration value")


class QueryConstraints(BaseModel):
    """
    Immutable container aggregating all resource and execution constraints for an EngineeringQuery.
    """
    model_config = ConfigDict(frozen=True)

    time_budget: TimeBudgetConstraint = Field(default_factory=TimeBudgetConstraint, description="Time budget constraint")
    memory_budget: MemoryBudgetConstraint = Field(default_factory=MemoryBudgetConstraint, description="Memory budget constraint")
    node_budget: NodeBudgetConstraint = Field(default_factory=NodeBudgetConstraint, description="Visited node budget")
    traversal_budget: TraversalBudgetConstraint = Field(default_factory=TraversalBudgetConstraint, description="Edge step budget")
    result_limit: ResultLimitConstraint = Field(default_factory=ResultLimitConstraint, description="Result count limit")
    complexity_limit: ComplexityLimitConstraint = Field(default_factory=ComplexityLimitConstraint, description="AST complexity limit")
    custom_constraints: Tuple[PlannerConstraint, ...] = Field(default_factory=tuple, description="Custom planner constraints")


__all__ = [
    "TimeBudgetConstraint",
    "MemoryBudgetConstraint",
    "NodeBudgetConstraint",
    "TraversalBudgetConstraint",
    "ResultLimitConstraint",
    "ComplexityLimitConstraint",
    "PlannerConstraint",
    "QueryConstraints",
]
