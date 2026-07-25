"""
core/type_reference_edges/serialization.py
-------------------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for Type Reference EdgeCollection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.type_reference_edges.exceptions import TypeReferenceSerializationError

TYPE_REFERENCE_EDGE_COLLECTION_VERSION = "4.5.0"


def type_reference_collection_to_dict(collection: Any) -> Dict[str, Any]:
    """
    Convert a Type Reference EdgeCollection instance into a serializable dictionary with versioning tag.
    """
    try:
        data = collection.model_dump(mode="json")
        data["_schema_version"] = TYPE_REFERENCE_EDGE_COLLECTION_VERSION
        return data
    except Exception as e:
        raise TypeReferenceSerializationError(f"Failed to serialize Type Reference EdgeCollection to dict: {str(e)}") from e


def dict_to_type_reference_collection(data: Dict[str, Any], collection_cls: Any) -> Any:
    """
    Construct a Type Reference EdgeCollection instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return collection_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise TypeReferenceSerializationError(f"Validation error deserializing Type Reference EdgeCollection: {str(ve)}") from ve
    except Exception as e:
        raise TypeReferenceSerializationError(f"Failed to deserialize dict to Type Reference EdgeCollection: {str(e)}") from e


def type_reference_collection_to_json(collection: Any, indent: bool = False) -> str:
    """
    Serialize a Type Reference EdgeCollection instance into a JSON string.
    """
    try:
        data = type_reference_collection_to_dict(collection)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise TypeReferenceSerializationError(f"Failed to serialize Type Reference EdgeCollection to JSON: {str(e)}") from e


def json_to_type_reference_collection(json_str: str, collection_cls: Any) -> Any:
    """
    Deserialize a JSON string into a Type Reference EdgeCollection instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_type_reference_collection(data, collection_cls)
    except json.JSONDecodeError as jde:
        raise TypeReferenceSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise TypeReferenceSerializationError(f"Failed to deserialize JSON to Type Reference EdgeCollection: {str(e)}") from e


def hash_type_reference_collection(collection: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a Type Reference EdgeCollection.
    """
    json_bytes = type_reference_collection_to_json(collection).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
