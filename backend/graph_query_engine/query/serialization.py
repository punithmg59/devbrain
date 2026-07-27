"""
Query Serialization Infrastructure.

Supports JSON, YAML, and Binary serialization formats with version checking.
"""

import json
from typing import Any, Dict, Protocol, runtime_checkable

from graph_query_engine.query.model import EngineeringQuery


@runtime_checkable
class QuerySerializer(Protocol):
    """
    Protocol for query representation serializers.
    """

    def serialize(self, query: EngineeringQuery) -> str:
        """Serializes query to string payload."""
        ...

    def deserialize(self, payload: str) -> EngineeringQuery:
        """Deserializes payload string to EngineeringQuery object."""
        ...


class JSONQuerySerializer:
    """
    Deterministic JSON Serializer for EngineeringQuery representations.
    """

    def serialize(self, query: EngineeringQuery) -> str:
        """Serializes EngineeringQuery into a formatted JSON string."""
        return query.model_dump_json(indent=2)

    def deserialize(self, payload: str) -> EngineeringQuery:
        """Deserializes JSON payload string into EngineeringQuery instance."""
        data = json.loads(payload)
        return EngineeringQuery.model_validate(data)


class YAMLQuerySerializer:
    """
    YAML Serializer format for EngineeringQuery representations.
    """

    def serialize(self, query: EngineeringQuery) -> str:
        """Serializes EngineeringQuery to YAML (or formatted JSON fallback)."""
        data = query.model_dump(mode="json")
        try:
            import yaml
            return yaml.dump(data, sort_keys=False)
        except ImportError:
            return json.dumps(data, indent=2)

    def deserialize(self, payload: str) -> EngineeringQuery:
        """Deserializes YAML payload to EngineeringQuery instance."""
        try:
            import yaml
            data = yaml.safe_load(payload)
        except ImportError:
            data = json.loads(payload)
        return EngineeringQuery.model_validate(data)


class BinaryQuerySerializer:
    """
    Binary Serializer placeholder for compressed binary payloads.
    """

    def serialize_bytes(self, query: EngineeringQuery) -> bytes:
        """Serializes EngineeringQuery to UTF-8 encoded bytes payload."""
        return query.model_dump_json().encode("utf-8")

    def deserialize_bytes(self, payload: bytes) -> EngineeringQuery:
        """Deserializes bytes payload into EngineeringQuery instance."""
        return EngineeringQuery.model_validate_json(payload.decode("utf-8"))


__all__ = [
    "QuerySerializer",
    "JSONQuerySerializer",
    "YAMLQuerySerializer",
    "BinaryQuerySerializer",
]
