# backend/graph_query_engine/optimizer/serialization.py
"""Serialization utilities for the Planner Optimizer.
Provides JSON, YAML, and Binary serializers for PhysicalPlan, OptimizedPhysicalPlan,
and OptimizationReport objects.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Union

from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .report import OptimizationReport

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class JSONOptimizerSerializer:
    """JSON serializer for physical plans and optimization reports."""

    @staticmethod
    def serialize(obj: Union[PhysicalPlan, OptimizedPhysicalPlan, OptimizationReport]) -> str:
        """Serializes a model object to a JSON string."""
        if hasattr(obj, "model_dump_json"):
            # Pydantic v2
            return obj.model_dump_json(indent=2)
        elif hasattr(obj, "json"):
            # Pydantic v1
            return obj.json(indent=2)
        else:
            return json.dumps(obj, default=str, indent=2)

    @staticmethod
    def deserialize_physical_plan(data: str) -> PhysicalPlan:
        """Deserializes a JSON string into a PhysicalPlan."""
        d = json.loads(data)
        return PhysicalPlan(**d)

    @staticmethod
    def deserialize_optimized_plan(data: str) -> OptimizedPhysicalPlan:
        """Deserializes a JSON string into an OptimizedPhysicalPlan."""
        d = json.loads(data)
        return OptimizedPhysicalPlan(**d)


class YAMLOptimizerSerializer:
    """YAML serializer for physical plans and optimization reports."""

    @staticmethod
    def serialize(obj: Union[PhysicalPlan, OptimizedPhysicalPlan, OptimizationReport]) -> str:
        """Serializes a model object to a YAML string."""
        if hasattr(obj, "model_dump"):
            d = obj.model_dump()
        elif hasattr(obj, "dict"):
            d = obj.dict()
        else:
            d = dict(obj)

        if HAS_YAML:
            return yaml.safe_dump(d, sort_keys=False)
        else:
            # Fallback simple formatted output
            return json.dumps(d, default=str, indent=2)

    @staticmethod
    def deserialize_physical_plan(data: str) -> PhysicalPlan:
        """Deserializes a YAML string into a PhysicalPlan."""
        if HAS_YAML:
            d = yaml.safe_load(data)
        else:
            d = json.loads(data)
        return PhysicalPlan(**d)

    @staticmethod
    def deserialize_optimized_plan(data: str) -> OptimizedPhysicalPlan:
        """Deserializes a YAML string into an OptimizedPhysicalPlan."""
        if HAS_YAML:
            d = yaml.safe_load(data)
        else:
            d = json.loads(data)
        return OptimizedPhysicalPlan(**d)


class BinaryOptimizerSerializer:
    """Binary serializer placeholder (e.g. for MessagePack / Protocol Buffers serialization)."""

    @staticmethod
    def serialize(obj: Union[PhysicalPlan, OptimizedPhysicalPlan, OptimizationReport]) -> bytes:
        """Serializes a model object into binary bytes (UTF-8 encoded JSON payload)."""
        json_str = JSONOptimizerSerializer.serialize(obj)
        return json_str.encode("utf-8")

    @staticmethod
    def deserialize_physical_plan(data: bytes) -> PhysicalPlan:
        """Deserializes binary bytes into a PhysicalPlan."""
        json_str = data.decode("utf-8")
        return JSONOptimizerSerializer.deserialize_physical_plan(json_str)

    @staticmethod
    def deserialize_optimized_plan(data: bytes) -> OptimizedPhysicalPlan:
        """Deserializes binary bytes into an OptimizedPhysicalPlan."""
        json_str = data.decode("utf-8")
        return JSONOptimizerSerializer.deserialize_optimized_plan(json_str)


__all__ = [
    "JSONOptimizerSerializer",
    "YAMLOptimizerSerializer",
    "BinaryOptimizerSerializer",
]
