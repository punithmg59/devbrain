# backend/graph_query_engine/optimizer/contracts.py
"""Core contracts for the Planner Optimizer subsystem.
Defines the immutable representations of a PhysicalPlan and an
OptimizedPhysicalPlan. Both are frozen Pydantic models to guarantee
immutability throughout the optimization pipeline.
"""

from __future__ import annotations

from typing import List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


class PhysicalPlan(BaseModel):
    """Immutable representation of a validated PhysicalPlan."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    operators: List[Dict[str, Any]] = Field(..., description="Ordered list of physical operators")


class OptimizedPhysicalPlan(BaseModel):
    """Immutable OptimizedPhysicalPlan produced by the optimizer."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    operators: List[Dict[str, Any]] = Field(..., description="Ordered list of optimized physical operators")


__all__ = ["PhysicalPlan", "OptimizedPhysicalPlan"]
