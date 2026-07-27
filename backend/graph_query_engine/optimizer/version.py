# backend/graph_query_engine/optimizer/version.py
"""Versioning models for the Planner Optimizer subsystem.
All models are immutable (frozen) Pydantic BaseModel subclasses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class OptimizerVersion(BaseModel):
    """Version of the optimizer package itself."""

    model_config = ConfigDict(frozen=True)

    major: int = Field(..., description="Major version number")
    minor: int = Field(..., description="Minor version number")
    patch: int = Field(..., description="Patch version number")


class OptimizationRuleVersion(BaseModel):
    """Version identifier for a specific optimization rule implementation."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Rule name identifier")
    version: str = Field(..., description="Semantic version string, e.g., '1.0.0'")


class CompatibilityVersion(BaseModel):
    """Compatibility level between optimizer and other planner layers."""

    model_config = ConfigDict(frozen=True)

    optimizer_version: OptimizerVersion = Field(...)
    physical_plan_version: str = Field(..., description="Version string of the PhysicalPlan schema")
    api_version: str = Field(..., description="Version of the planner API this optimizer targets")


__all__ = ["OptimizerVersion", "OptimizationRuleVersion", "CompatibilityVersion"]
