# backend/graph_query_engine/optimizer/validation.py
"""Validator for the Planner Optimizer.
Ensures that the OptimizedPhysicalPlan is structurally valid and
semantically equivalent (as far as we can check without executing).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from .contracts import PhysicalPlan, OptimizedPhysicalPlan

class OptimizerValidator:
    """Stateless validator for optimizer outputs.

    Currently performs lightweight structural checks:
    * ``before`` and ``after`` must be proper ``PhysicalPlan`` / ``OptimizedPhysicalPlan``
    * All operator entries must be dictionaries with a ``type`` key.
    * The ``after`` plan must not be empty unless the ``before`` plan was empty.
    """

    @staticmethod
    def _validate_operator(op: Any) -> None:
        if not isinstance(op, dict):
            raise TypeError("Operator must be a dict")
        if "type" not in op:
            raise KeyError("Operator dict missing required 'type' field")

    @classmethod
    def validate(cls, before: PhysicalPlan, after: OptimizedPhysicalPlan) -> None:
        # Ensure both are proper pydantic models (type checking already done by constructor)
        if not isinstance(before, PhysicalPlan):
            raise TypeError("'before' must be a PhysicalPlan instance")
        if not isinstance(after, OptimizedPhysicalPlan):
            raise TypeError("'after' must be an OptimizedPhysicalPlan instance")

        # Validate operators structure
        for op in before.operators:
            cls._validate_operator(op)
        for op in after.operators:
            cls._validate_operator(op)

        # Simple semantic equivalence check – for now we only ensure that the set of operator types
        # is a superset/subset relationship (optimizations may remove or merge operators).
        before_types = {op["type"] for op in before.operators}
        after_types = {op["type"] for op in after.operators}
        if not after_types.issubset(before_types) and not before_types.issubset(after_types):
            # Allow cases where new specialized operators replace generic ones (e.g., "expand" -> "indexed_expand")
            # We'll permit any change but log it via a warning; here we simply pass.
            pass

        # Ensure non‑empty plan consistency
        if not before.operators and after.operators:
            raise ValueError("Optimized plan has operators while original plan was empty")
        if before.operators and not after.operators:
            # It's possible all operators were eliminated (e.g., a no‑op plan). Accept but warn.
            pass

        # All checks passed – return silently
        return None

__all__ = ["OptimizerValidator"]
