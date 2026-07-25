"""
core/symbol_extractor/serialization.py
---------------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for RawSymbolCollection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.symbol_extractor.exceptions import SymbolExtractionSerializationError

RAW_SYMBOL_COLLECTION_VERSION = "3.3.0"


def collection_to_dict(collection: Any) -> Dict[str, Any]:
    """
    Convert a RawSymbolCollection instance into a serializable dictionary with versioning tag.
    """
    try:
        data = collection.model_dump(mode="json")
        data["_schema_version"] = RAW_SYMBOL_COLLECTION_VERSION
        return data
    except Exception as e:
        raise SymbolExtractionSerializationError(f"Failed to serialize RawSymbolCollection to dict: {str(e)}") from e


def dict_to_collection(data: Dict[str, Any], collection_cls: Any) -> Any:
    """
    Construct a RawSymbolCollection instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return collection_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise SymbolExtractionSerializationError(f"Validation error deserializing RawSymbolCollection: {str(ve)}") from ve
    except Exception as e:
        raise SymbolExtractionSerializationError(f"Failed to deserialize dict to RawSymbolCollection: {str(e)}") from e


def collection_to_json(collection: Any, indent: bool = False) -> str:
    """
    Serialize a RawSymbolCollection instance into a JSON string.
    """
    try:
        data = collection_to_dict(collection)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise SymbolExtractionSerializationError(f"Failed to serialize RawSymbolCollection to JSON: {str(e)}") from e


def json_to_collection(json_str: str, collection_cls: Any) -> Any:
    """
    Deserialize a JSON string into a RawSymbolCollection instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_collection(data, collection_cls)
    except json.JSONDecodeError as jde:
        raise SymbolExtractionSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise SymbolExtractionSerializationError(f"Failed to deserialize JSON to RawSymbolCollection: {str(e)}") from e


def hash_collection(collection: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a RawSymbolCollection.
    """
    json_bytes = collection_to_json(collection).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
