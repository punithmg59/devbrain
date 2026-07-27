"""
Execution Plan Serialization Infrastructure.

Supports JSON, YAML, and Binary serialization formats for ExecutionPlan models.
"""

import json
from typing import Any, Dict, Protocol, runtime_checkable

from graph_query_engine.execution.plan import ExecutionPlan


@runtime_checkable
class ExecutionPlanSerializer(Protocol):
    """Protocol for ExecutionPlan serializers."""

    def serialize(self, plan: ExecutionPlan) -> str:
        """Serializes ExecutionPlan to string payload."""
        ...

    def deserialize(self, payload: str) -> ExecutionPlan:
        """Deserializes string payload into ExecutionPlan object."""
        ...


class JSONExecutionPlanSerializer:
    """Deterministic JSON Serializer for ExecutionPlan models."""

    def serialize(self, plan: ExecutionPlan) -> str:
        """Serializes ExecutionPlan to formatted JSON string."""
        return plan.model_dump_json(indent=2)

    def deserialize(self, payload: str) -> ExecutionPlan:
        """Deserializes JSON string into ExecutionPlan instance."""
        data = json.loads(payload)
        return ExecutionPlan.model_validate(data)


class YAMLExecutionPlanSerializer:
    """YAML Serializer for ExecutionPlan models."""

    def serialize(self, plan: ExecutionPlan) -> str:
        """Serializes ExecutionPlan to YAML string."""
        data = plan.model_dump(mode="json")
        try:
            import yaml
            return yaml.dump(data, sort_keys=False)
        except ImportError:
            return json.dumps(data, indent=2)

    def deserialize(self, payload: str) -> ExecutionPlan:
        """Deserializes YAML string into ExecutionPlan instance."""
        try:
            import yaml
            data = yaml.safe_load(payload)
        except ImportError:
            data = json.loads(payload)
        return ExecutionPlan.model_validate(data)


class BinaryExecutionPlanSerializer:
    """Binary Serializer for ExecutionPlan payloads."""

    def serialize_bytes(self, plan: ExecutionPlan) -> bytes:
        """Serializes ExecutionPlan into UTF-8 encoded bytes payload."""
        return plan.model_dump_json().encode("utf-8")

    def deserialize_bytes(self, payload: bytes) -> ExecutionPlan:
        """Deserializes UTF-8 encoded bytes into ExecutionPlan instance."""
        return ExecutionPlan.model_validate_json(payload.decode("utf-8"))


__all__ = [
    "ExecutionPlanSerializer",
    "JSONExecutionPlanSerializer",
    "YAMLExecutionPlanSerializer",
    "BinaryExecutionPlanSerializer",
]
