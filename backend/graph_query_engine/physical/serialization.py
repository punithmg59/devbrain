"""
Physical Plan Serialization Infrastructure.

Supports JSON, YAML, and Binary serialization formats for PhysicalPlan models.
"""

import json
from typing import Any, Dict, Protocol, runtime_checkable

from graph_query_engine.physical.plan import PhysicalPlan


@runtime_checkable
class PhysicalPlanSerializer(Protocol):
    """Protocol for PhysicalPlan serializers."""

    def serialize(self, plan: PhysicalPlan) -> str:
        """Serializes PhysicalPlan to string payload."""
        ...

    def deserialize(self, payload: str) -> PhysicalPlan:
        """Deserializes string payload into PhysicalPlan object."""
        ...


class JSONPhysicalPlanSerializer:
    """Deterministic JSON Serializer for PhysicalPlan models."""

    def serialize(self, plan: PhysicalPlan) -> str:
        """Serializes PhysicalPlan to formatted JSON string."""
        return plan.model_dump_json(indent=2)

    def deserialize(self, payload: str) -> PhysicalPlan:
        """Deserializes JSON string into PhysicalPlan instance."""
        data = json.loads(payload)
        return PhysicalPlan.model_validate(data)


class YAMLPhysicalPlanSerializer:
    """YAML Serializer for PhysicalPlan models."""

    def serialize(self, plan: PhysicalPlan) -> str:
        """Serializes PhysicalPlan to YAML string."""
        data = plan.model_dump(mode="json")
        try:
            import yaml
            return yaml.dump(data, sort_keys=False)
        except ImportError:
            return json.dumps(data, indent=2)

    def deserialize(self, payload: str) -> PhysicalPlan:
        """Deserializes YAML string into PhysicalPlan instance."""
        try:
            import yaml
            data = yaml.safe_load(payload)
        except ImportError:
            data = json.loads(payload)
        return PhysicalPlan.model_validate(data)


class BinaryPhysicalPlanSerializer:
    """Binary Serializer for PhysicalPlan payloads."""

    def serialize_bytes(self, plan: PhysicalPlan) -> bytes:
        """Serializes PhysicalPlan into UTF-8 encoded bytes payload."""
        return plan.model_dump_json().encode("utf-8")

    def deserialize_bytes(self, payload: bytes) -> PhysicalPlan:
        """Deserializes UTF-8 encoded bytes into PhysicalPlan instance."""
        return PhysicalPlan.model_validate_json(payload.decode("utf-8"))


__all__ = [
    "PhysicalPlanSerializer",
    "JSONPhysicalPlanSerializer",
    "YAMLPhysicalPlanSerializer",
    "BinaryPhysicalPlanSerializer",
]
