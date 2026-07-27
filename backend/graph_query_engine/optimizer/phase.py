# backend/graph_query_engine/optimizer/phase.py
"""Immutable definition of an optimization phase."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, ConfigDict

from .rules import OptimizationRule


class OptimizationPhase(BaseModel):
    """Immutable phase in the optimization pipeline."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(...)
    priority: int = Field(0, description="Phase priority – lower executes first")
    enabled: bool = Field(True)
    rules: List[OptimizationRule] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


__all__ = ["OptimizationPhase"]
