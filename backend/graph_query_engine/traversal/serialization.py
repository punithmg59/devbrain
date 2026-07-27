# backend/graph_query_engine/traversal/serialization.py
"""Serialization utilities for TraversalResult and related traversal models.
Supports JSON, YAML, and Binary serializers.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Union

from .result import TraversalResult

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class JSONTraversalSerializer:
    """JSON serializer for TraversalResult."""

    @staticmethod
    def serialize(result: TraversalResult) -> str:
        """Serializes TraversalResult model to a JSON string."""
        if hasattr(result, "model_dump_json"):
            return result.model_dump_json(indent=2)
        elif hasattr(result, "json"):
            return result.json(indent=2)
        else:
            return json.dumps(result, default=str, indent=2)

    @staticmethod
    def deserialize(data: str) -> TraversalResult:
        """Deserializes a JSON string into a TraversalResult."""
        d = json.loads(data)
        return TraversalResult(**d)


class YAMLTraversalSerializer:
    """YAML serializer for TraversalResult."""

    @staticmethod
    def serialize(result: TraversalResult) -> str:
        """Serializes TraversalResult model to a YAML string."""
        if hasattr(result, "model_dump"):
            d = result.model_dump()
        elif hasattr(result, "dict"):
            d = result.dict()
        else:
            d = dict(result)

        if HAS_YAML:
            return yaml.safe_dump(d, sort_keys=False)
        else:
            return json.dumps(d, default=str, indent=2)

    @staticmethod
    def deserialize(data: str) -> TraversalResult:
        """Deserializes a YAML string into a TraversalResult."""
        if HAS_YAML:
            d = yaml.safe_load(data)
        else:
            d = json.loads(data)
        return TraversalResult(**d)


class BinaryTraversalSerializer:
    """Binary serializer placeholder (UTF-8 encoded JSON bytes)."""

    @staticmethod
    def serialize(result: TraversalResult) -> bytes:
        """Serializes TraversalResult into binary bytes."""
        json_str = JSONTraversalSerializer.serialize(result)
        return json_str.encode("utf-8")

    @staticmethod
    def deserialize(data: bytes) -> TraversalResult:
        """Deserializes binary bytes into a TraversalResult."""
        json_str = data.decode("utf-8")
        return JSONTraversalSerializer.deserialize(json_str)


__all__ = [
    "JSONTraversalSerializer",
    "YAMLTraversalSerializer",
    "BinaryTraversalSerializer",
]
