"""
core/symbols/serialization.py
------------------------------
Serialization, Deserialization, Hashing, and Versioning logic for Symbols.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from pydantic import ValidationError

from core.symbols.exceptions import SymbolSerializationError
from core.symbols.models import Symbol

SYMBOL_MODEL_VERSION = "3.1.0"


def symbol_to_dict(symbol: Symbol) -> Dict[str, Any]:
    """
    Convert a Symbol instance into a serializable dictionary with versioning tag.
    """
    try:
        data = symbol.model_dump(mode="json")
        data["_schema_version"] = SYMBOL_MODEL_VERSION
        return data
    except Exception as e:
        raise SymbolSerializationError(f"Failed to serialize Symbol to dict: {str(e)}") from e


def dict_to_symbol(data: Dict[str, Any]) -> Symbol:
    """
    Construct a Symbol instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return Symbol.model_validate(clean_data)
    except ValidationError as ve:
        raise SymbolSerializationError(f"Validation error deserializing Symbol: {str(ve)}") from ve
    except Exception as e:
        raise SymbolSerializationError(f"Failed to deserialize dict to Symbol: {str(e)}") from e


def symbol_to_json(symbol: Symbol, indent: bool = False) -> str:
    """
    Serialize a Symbol instance into a JSON string.
    """
    try:
        data = symbol_to_dict(symbol)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise SymbolSerializationError(f"Failed to serialize Symbol to JSON: {str(e)}") from e


def json_to_symbol(json_str: str) -> Symbol:
    """
    Deserialize a JSON string into a Symbol instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_symbol(data)
    except json.JSONDecodeError as jde:
        raise SymbolSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise SymbolSerializationError(f"Failed to deserialize JSON to Symbol: {str(e)}") from e


def hash_symbol(symbol: Symbol) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a Symbol.
    """
    json_bytes = symbol_to_json(symbol).encode("utf-8")
    import hashlib
    return hashlib.sha256(json_bytes).hexdigest()


def are_symbols_equal(s1: Symbol, s2: Symbol) -> bool:
    """
    Test deep structural equality between two Symbol instances.
    """
    return s1 == s2
