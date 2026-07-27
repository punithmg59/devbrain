# backend/graph_query_engine/optimizer/rules.py
"""Core abstract rule definition for the Optimization Rule Engine.
All concrete optimization rules must inherit from :class:`OptimizationRule` and be immutable.
"""

from __future__ import annotations

import abc
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict

from .context import OptimizationRuleContext
from .result import OptimizationRuleResult


class OptimizationRule(BaseModel, abc.ABC):
    """Immutable abstract base class for an optimizer rewrite rule."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    rule_id: str = Field(..., description="Unique rule identifier")
    version: str = Field(..., description="Rule version string, e.g., '1.0.0'")
    category: str = Field(..., description="Rule category, e.g., 'Filter'")
    priority: int = Field(0, description="Ordering priority inside a phase (lower first)")
    enabled: bool = Field(True, description="Flag to enable/disable the rule")

    @abc.abstractmethod
    def can_apply(self, context: OptimizationRuleContext) -> bool:
        """Return True if the rule is applicable to the supplied context."""

    @abc.abstractmethod
    def apply(self, context: OptimizationRuleContext) -> OptimizationRuleResult:
        """Perform the transformation and return an OptimizationRuleResult."""

    def describe(self) -> str:
        """Human-readable description of the rule."""
        return f"Rule {self.rule_id} (v{self.version}) – category: {self.category}"

    def estimate_benefit(self, context: OptimizationRuleContext) -> Optional[float]:
        """Optional heuristic estimate of benefit."""
        return None

    def _debug(self, msg: str) -> None:
        pass


__all__ = ["OptimizationRule"]
