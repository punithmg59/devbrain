"""
Cost Report Serialization Infrastructure.

Supports JSON, YAML, and Binary serialization formats for CostReport models.
"""

import json
from typing import Any, Dict, Protocol, runtime_checkable

from graph_query_engine.cost.estimate import CostReport


@runtime_checkable
class CostReportSerializer(Protocol):
    """Protocol for CostReport serializers."""

    def serialize(self, report: CostReport) -> str:
        """Serializes CostReport to string payload."""
        ...

    def deserialize(self, payload: str) -> CostReport:
        """Deserializes string payload into CostReport object."""
        ...


class JSONCostReportSerializer:
    """Deterministic JSON Serializer for CostReport models."""

    def serialize(self, report: CostReport) -> str:
        """Serializes CostReport to formatted JSON string."""
        return report.model_dump_json(indent=2)

    def deserialize(self, payload: str) -> CostReport:
        """Deserializes JSON string into CostReport instance."""
        data = json.loads(payload)
        return CostReport.model_validate(data)


class YAMLCostReportSerializer:
    """YAML Serializer for CostReport models."""

    def serialize(self, report: CostReport) -> str:
        """Serializes CostReport to YAML string."""
        data = report.model_dump(mode="json")
        try:
            import yaml
            return yaml.dump(data, sort_keys=False)
        except ImportError:
            return json.dumps(data, indent=2)

    def deserialize(self, payload: str) -> CostReport:
        """Deserializes YAML string into CostReport instance."""
        try:
            import yaml
            data = yaml.safe_load(payload)
        except ImportError:
            data = json.loads(payload)
        return CostReport.model_validate(data)


class BinaryCostReportSerializer:
    """Binary Serializer for CostReport payloads."""

    def serialize_bytes(self, report: CostReport) -> bytes:
        """Serializes CostReport into UTF-8 encoded bytes payload."""
        return report.model_dump_json().encode("utf-8")

    def deserialize_bytes(self, payload: bytes) -> CostReport:
        """Deserializes UTF-8 encoded bytes into CostReport instance."""
        return CostReport.model_validate_json(payload.decode("utf-8"))


__all__ = [
    "CostReportSerializer",
    "JSONCostReportSerializer",
    "YAMLCostReportSerializer",
    "BinaryCostReportSerializer",
]
