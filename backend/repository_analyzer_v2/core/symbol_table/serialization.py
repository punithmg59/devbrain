"""
core/symbol_table/serialization.py
----------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for SymbolTable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.symbol_table.exceptions import SymbolTableSerializationError

SYMBOL_TABLE_VERSION = "3.5.0"


def table_to_dict(table: Any) -> Dict[str, Any]:
    """
    Convert a SymbolTable instance into a serializable dictionary with versioning tag.
    """
    try:
        data = table.model_dump(mode="json")
        data["_schema_version"] = SYMBOL_TABLE_VERSION
        return data
    except Exception as e:
        raise SymbolTableSerializationError(f"Failed to serialize SymbolTable to dict: {str(e)}") from e


def dict_to_table(data: Dict[str, Any], table_cls: Any) -> Any:
    """
    Construct a SymbolTable instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return table_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise SymbolTableSerializationError(f"Validation error deserializing SymbolTable: {str(ve)}") from ve
    except Exception as e:
        raise SymbolTableSerializationError(f"Failed to deserialize dict to SymbolTable: {str(e)}") from e


def table_to_json(table: Any, indent: bool = False) -> str:
    """
    Serialize a SymbolTable instance into a JSON string.
    """
    try:
        data = table_to_dict(table)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise SymbolTableSerializationError(f"Failed to serialize SymbolTable to JSON: {str(e)}") from e


def json_to_table(json_str: str, table_cls: Any) -> Any:
    """
    Deserialize a JSON string into a SymbolTable instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_table(data, table_cls)
    except json.JSONDecodeError as jde:
        raise SymbolTableSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise SymbolTableSerializationError(f"Failed to deserialize JSON to SymbolTable: {str(e)}") from e


def hash_symbol_table(table: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a SymbolTable.
    """
    json_bytes = table_to_json(table).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
