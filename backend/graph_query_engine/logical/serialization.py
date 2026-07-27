"""
Logical Plan Serialization Infrastructure.

Supports JSON, YAML, and Binary serialization formats for LogicalPlan models.
"""

import json
from typing import Any, Dict, Protocol, runtime_checkable

from graph_query_engine.logical.plan import LogicalPlan


@runtime_checkable
class LogicalPlanSerializer(Protocol):
    """
    Protocol for LogicalPlan serializers.
    """

    def serialize(self, plan: LogicalPlan) -> str:
        """Serializes LogicalPlan to string payload."""
        ...

    def deserialize(self, payload: str) -> LogicalPlan:
        """Deserializes string payload to LogicalPlan object."""
        ...


class JSONLogicalPlanSerializer:
    """
    Deterministic JSON Serializer for LogicalPlan models.
    """

    def serialize(self, plan: LogicalPlan) -> str:
        """Serializes LogicalPlan to formatted JSON string."""
        return plan.model_dump_json(indent=2)

    def deserialize(self, payload: str) -> LogicalPlan:
        """Deserializes JSON payload string into LogicalPlan instance."""
        data = json.loads(payload)
        return LogicalPlan.model_validate(data)


class YAMLLogicalPlanSerializer:
    """
    YAML Serializer for LogicalPlan models.
    """

    def serialize(self, plan: LogicalPlan) -> str:
        """Serializes LogicalPlan to YAML (or JSON fallback)."""
        data = plan.model_dump(mode="json")
        try:
            import yaml
            return yaml.dump(data, sort_keys=False)
        except ImportError:
            return json.dumps(data, indent=2)

    def deserialize(self, payload: str) -> LogicalPlan:
        """Deserializes YAML payload string into LogicalPlan instance."""
        try:
            import yaml
            data = yaml.safe_load(payload)
        except ImportError:
            data = json.loads(payload)
        return LogicalPlan.model_validate(data)


class BinaryLogicalPlanSerializer:
    """
    Binary Serializer for compressed LogicalPlan payloads.
    """

    def serialize_bytes(self, plan: LogicalPlan) -> bytes:
        """Serializes LogicalPlan into UTF-8 encoded bytes payload."""
        return plan.model_dump_json().encode("utf-8")

    def deserialize_bytes(self, payload: bytes) -> LogicalPlan:
        """Deserializes UTF-8 encoded bytes payload into LogicalPlan instance."""
        return LogicalPlan.model_validate_json(payload.decode("utf-8"))


__all__ = [
    "LogicalPlanSerializer",
    "JSONLogicalPlanSerializer",
    "YAMLLogicalPlanSerializer",
    "BinaryLogicalPlanSerializer",
]
