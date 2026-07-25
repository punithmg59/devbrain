"""
core/symbol_identity/serialization.py
--------------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for CanonicalSymbolCollection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.symbol_identity.exceptions import IdentitySerializationError

CANONICAL_SYMBOL_COLLECTION_VERSION = "3.4.0"


def canonical_collection_to_dict(collection: Any) -> Dict[str, Any]:
    """
    Convert a CanonicalSymbolCollection instance into a serializable dictionary with versioning tag.
    """
    try:
        data = collection.model_dump(mode="json")
        data["_schema_version"] = CANONICAL_SYMBOL_COLLECTION_VERSION
        return data
    except Exception as e:
        raise IdentitySerializationError(f"Failed to serialize CanonicalSymbolCollection to dict: {str(e)}") from e


def dict_to_canonical_collection(data: Dict[str, Any], collection_cls: Any) -> Any:
    """
    Construct a CanonicalSymbolCollection instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return collection_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise IdentitySerializationError(f"Validation error deserializing CanonicalSymbolCollection: {str(ve)}") from ve
    except Exception as e:
        raise IdentitySerializationError(f"Failed to deserialize dict to CanonicalSymbolCollection: {str(e)}") from e


def canonical_collection_to_json(collection: Any, indent: bool = False) -> str:
    """
    Serialize a CanonicalSymbolCollection instance into a JSON string.
    """
    try:
        data = canonical_collection_to_dict(collection)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise IdentitySerializationError(f"Failed to serialize CanonicalSymbolCollection to JSON: {str(e)}") from e


def json_to_canonical_collection(json_str: str, collection_cls: Any) -> Any:
    """
    Deserialize a JSON string into a CanonicalSymbolCollection instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_canonical_collection(data, collection_cls)
    except json.JSONDecodeError as jde:
        raise IdentitySerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise IdentitySerializationError(f"Failed to deserialize JSON to CanonicalSymbolCollection: {str(e)}") from e


def hash_canonical_collection(collection: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a CanonicalSymbolCollection.
    """
    json_bytes = canonical_collection_to_json(collection).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
