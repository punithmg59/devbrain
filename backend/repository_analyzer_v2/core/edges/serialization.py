"""
core/edges/serialization.py
----------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for EdgeCollection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.edges.exceptions import EdgeSerializationError

EDGE_COLLECTION_VERSION = "4.1.0"


def edge_collection_to_dict(collection: Any) -> Dict[str, Any]:
    """
    Convert an EdgeCollection instance into a serializable dictionary with versioning tag.
    """
    try:
        data = collection.model_dump(mode="json")
        data["_schema_version"] = EDGE_COLLECTION_VERSION
        return data
    except Exception as e:
        raise EdgeSerializationError(f"Failed to serialize EdgeCollection to dict: {str(e)}") from e


def dict_to_edge_collection(data: Dict[str, Any], collection_cls: Any) -> Any:
    """
    Construct an EdgeCollection instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return collection_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise EdgeSerializationError(f"Validation error deserializing EdgeCollection: {str(ve)}") from ve
    except Exception as e:
        raise EdgeSerializationError(f"Failed to deserialize dict to EdgeCollection: {str(e)}") from e


def edge_collection_to_json(collection: Any, indent: bool = False) -> str:
    """
    Serialize an EdgeCollection instance into a JSON string.
    """
    try:
        data = edge_collection_to_dict(collection)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise EdgeSerializationError(f"Failed to serialize EdgeCollection to JSON: {str(e)}") from e


def json_to_edge_collection(json_str: str, collection_cls: Any) -> Any:
    """
    Deserialize a JSON string into an EdgeCollection instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_edge_collection(data, collection_cls)
    except json.JSONDecodeError as jde:
        raise EdgeSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise EdgeSerializationError(f"Failed to deserialize JSON to EdgeCollection: {str(e)}") from e


def hash_edge_collection(collection: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of an EdgeCollection.
    """
    json_bytes = edge_collection_to_json(collection).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
