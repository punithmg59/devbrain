"""
core/namespaces/serialization.py
--------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for NamespaceTree.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.namespaces.exceptions import NamespaceSerializationError
from core.namespaces.tree import NAMESPACE_TREE_VERSION, NamespaceTree


def tree_to_dict(tree: NamespaceTree) -> Dict[str, Any]:
    """
    Convert a NamespaceTree instance into a serializable dictionary with versioning tag.
    """
    try:
        data = tree.model_dump(mode="json")
        data["_schema_version"] = NAMESPACE_TREE_VERSION
        return data
    except Exception as e:
        raise NamespaceSerializationError(f"Failed to serialize NamespaceTree to dict: {str(e)}") from e


def dict_to_tree(data: Dict[str, Any]) -> NamespaceTree:
    """
    Construct a NamespaceTree instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return NamespaceTree.model_validate(clean_data)
    except ValidationError as ve:
        raise NamespaceSerializationError(f"Validation error deserializing NamespaceTree: {str(ve)}") from ve
    except Exception as e:
        raise NamespaceSerializationError(f"Failed to deserialize dict to NamespaceTree: {str(e)}") from e


def tree_to_json(tree: NamespaceTree, indent: bool = False) -> str:
    """
    Serialize a NamespaceTree instance into a JSON string.
    """
    try:
        data = tree_to_dict(tree)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise NamespaceSerializationError(f"Failed to serialize NamespaceTree to JSON: {str(e)}") from e


def json_to_tree(json_str: str) -> NamespaceTree:
    """
    Deserialize a JSON string into a NamespaceTree instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_tree(data)
    except json.JSONDecodeError as jde:
        raise NamespaceSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise NamespaceSerializationError(f"Failed to deserialize JSON to NamespaceTree: {str(e)}") from e


def hash_tree(tree: NamespaceTree) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a NamespaceTree.
    """
    json_bytes = tree_to_json(tree).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
