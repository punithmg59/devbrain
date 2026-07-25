"""
core/dependency_graph/serialization.py
---------------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for DependencyGraph.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.dependency_graph.exceptions import GraphSerializationError

DEPENDENCY_GRAPH_VERSION = "4.6.0"


def dependency_graph_to_dict(graph: Any) -> Dict[str, Any]:
    """
    Convert a DependencyGraph instance into a serializable dictionary with versioning tag.
    """
    try:
        data = graph.model_dump(mode="json")
        data["_schema_version"] = DEPENDENCY_GRAPH_VERSION
        return data
    except Exception as e:
        raise GraphSerializationError(f"Failed to serialize DependencyGraph to dict: {str(e)}") from e


def dict_to_dependency_graph(data: Dict[str, Any], graph_cls: Any) -> Any:
    """
    Construct a DependencyGraph instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return graph_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise GraphSerializationError(f"Validation error deserializing DependencyGraph: {str(ve)}") from ve
    except Exception as e:
        raise GraphSerializationError(f"Failed to deserialize dict to DependencyGraph: {str(e)}") from e


def dependency_graph_to_json(graph: Any, indent: bool = False) -> str:
    """
    Serialize a DependencyGraph instance into a JSON string.
    """
    try:
        data = dependency_graph_to_dict(graph)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise GraphSerializationError(f"Failed to serialize DependencyGraph to JSON: {str(e)}") from e


def json_to_dependency_graph(json_str: str, graph_cls: Any) -> Any:
    """
    Deserialize a JSON string into a DependencyGraph instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_dependency_graph(data, graph_cls)
    except json.JSONDecodeError as jde:
        raise GraphSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise GraphSerializationError(f"Failed to deserialize JSON to DependencyGraph: {str(e)}") from e


def hash_dependency_graph(graph: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a DependencyGraph.
    """
    json_bytes = dependency_graph_to_json(graph).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
