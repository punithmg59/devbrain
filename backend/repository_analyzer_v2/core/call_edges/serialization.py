"""
core/call_edges/serialization.py
---------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for Call EdgeCollection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.call_edges.exceptions import CallSerializationError

CALL_EDGE_COLLECTION_VERSION = "4.3.0"


def call_collection_to_dict(collection: Any) -> Dict[str, Any]:
    """
    Convert a Call EdgeCollection instance into a serializable dictionary with versioning tag.
    """
    try:
        data = collection.model_dump(mode="json")
        data["_schema_version"] = CALL_EDGE_COLLECTION_VERSION
        return data
    except Exception as e:
        raise CallSerializationError(f"Failed to serialize Call EdgeCollection to dict: {str(e)}") from e


def dict_to_call_collection(data: Dict[str, Any], collection_cls: Any) -> Any:
    """
    Construct a Call EdgeCollection instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return collection_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise CallSerializationError(f"Validation error deserializing Call EdgeCollection: {str(ve)}") from ve
    except Exception as e:
        raise CallSerializationError(f"Failed to deserialize dict to Call EdgeCollection: {str(e)}") from e


def call_collection_to_json(collection: Any, indent: bool = False) -> str:
    """
    Serialize a Call EdgeCollection instance into a JSON string.
    """
    try:
        data = call_collection_to_dict(collection)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise CallSerializationError(f"Failed to serialize Call EdgeCollection to JSON: {str(e)}") from e


def json_to_call_collection(json_str: str, collection_cls: Any) -> Any:
    """
    Deserialize a JSON string into a Call EdgeCollection instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_call_collection(data, collection_cls)
    except json.JSONDecodeError as jde:
        raise CallSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise CallSerializationError(f"Failed to deserialize JSON to Call EdgeCollection: {str(e)}") from e


def hash_call_collection(collection: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a Call EdgeCollection.
    """
    json_bytes = call_collection_to_json(collection).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
