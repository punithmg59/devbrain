"""
Immutable Cost Estimates and Cost Report Value Objects.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import QueryId


class CostEstimate(BaseModel):
    """
    Immutable value object representing estimated execution costs and metrics for an operator or plan.
    """
    model_config = ConfigDict(frozen=True)

    cpu_cost: float = Field(default=0.0, ge=0.0, description="Estimated CPU work units")
    memory_cost: float = Field(default=0.0, ge=0.0, description="Estimated memory overhead bytes")
    traversal_cost: float = Field(default=0.0, ge=0.0, description="Estimated graph edge traversal cost units")
    estimated_cardinality: float = Field(default=1.0, ge=0.0, description="Estimated output row/entity count")
    estimated_selectivity: float = Field(default=1.0, ge=0.0, le=1.0, description="Estimated filter selectivity (0.0 to 1.0)")
    estimated_result_size_bytes: float = Field(default=0.0, ge=0.0, description="Estimated payload size in bytes")
    estimated_depth: float = Field(default=1.0, ge=0.0, description="Estimated tree or path depth")
    estimated_fan_out: float = Field(default=1.0, ge=0.0, description="Estimated average node fan-out degree")
    estimated_fan_in: float = Field(default=1.0, ge=0.0, description="Estimated average node fan-in degree")
    estimated_operator_cost: float = Field(default=0.0, ge=0.0, description="Self execution cost of the operator")
    estimated_total_cost: float = Field(default=0.0, ge=0.0, description="Cumulative cost including child inputs")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Estimation confidence score (0.0 to 1.0)")


class OperatorCostBreakdown(BaseModel):
    """
    Immutable binding associating a LogicalOperator ID with its calculated CostEstimate.
    """
    model_config = ConfigDict(frozen=True)

    operator_id: str = Field(..., description="Unique logical operator instance ID")
    operator_name: str = Field(..., description="Logical operator classification name")
    estimate: CostEstimate = Field(..., description="Calculated CostEstimate for this operator")


class CostReport(BaseModel):
    """
    Canonical immutable report produced by CostEstimator for a LogicalPlan.
    """
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(
        default_factory=lambda: f"creport_{uuid.uuid4().hex[:12]}",
        description="Unique CostReport identifier string",
    )
    plan_id: str = Field(..., description="Associated LogicalPlan plan_id")
    query_id: QueryId = Field(..., description="Associated source QueryId")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    total_cost_estimate: CostEstimate = Field(..., description="Cumulative total plan CostEstimate")
    operator_costs: Tuple[OperatorCostBreakdown, ...] = Field(default_factory=tuple, description="Breakdown of per-operator estimates")
    diagnostics: Tuple[str, ...] = Field(default_factory=tuple, description="Cost estimation diagnostics log")
    warnings: Tuple[str, ...] = Field(default_factory=tuple, description="Estimation warning messages")
    confidence_report: Dict[str, float] = Field(default_factory=dict, description="Confidence scores by operator")
    statistics_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of input statistics used")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes CostReport to python dict."""
        return self.model_dump(mode="python")


__all__ = [
    "CostEstimate",
    "OperatorCostBreakdown",
    "CostReport",
]
