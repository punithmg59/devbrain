"""
core/import_edges/serialization.py
-----------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for Import EdgeCollection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.import_edges.exceptions import ImportSerializationError

IMPORT_EDGE_COLLECTION_VERSION = "4.2.0"


def import_collection_to_dict(collection: Any) -> Dict[str, Any]:
    """
    Convert an Import EdgeCollection instance into a serializable dictionary with versioning tag.
    """
    try:
        data = collection.model_dump(mode="json")
        data["_schema_version"] = IMPORT_EDGE_COLLECTION_VERSION
        return data
    except Exception as e:
        raise ImportSerializationError(f"Failed to serialize Import EdgeCollection to dict: {str(e)}") from e


def dict_to_import_collection(data: Dict[str, Any], collection_cls: Any) -> Any:
    """
    Construct an Import EdgeCollection instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return collection_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise ImportSerializationError(f"Validation error deserializing Import EdgeCollection: {str(ve)}") from ve
    except Exception as e:
        raise ImportSerializationError(f"Failed to deserialize dict to Import EdgeCollection: {str(e)}") from e


def import_collection_to_json(collection: Any, indent: bool = False) -> str:
    """
    Serialize an Import EdgeCollection instance into a JSON string.
    """
    try:
        data = import_collection_to_dict(collection)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise ImportSerializationError(f"Failed to serialize Import EdgeCollection to JSON: {str(e)}") from e


def json_to_import_collection(json_str: str, collection_cls: Any) -> Any:
    """
    Deserialize a JSON string into an Import EdgeCollection instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_import_collection(data, collection_cls)
    except json.JSONDecodeError as jde:
        raise ImportSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise ImportSerializationError(f"Failed to deserialize JSON to Import EdgeCollection: {str(e)}") from e


def hash_import_collection(collection: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of an Import EdgeCollection.
    """
    json_bytes = import_collection_to_json(collection).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
