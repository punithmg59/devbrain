"""
core/symbol_builder/serialization.py
-------------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for SemanticRepository.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.symbol_builder.exceptions import PipelineSerializationError
from core.symbol_builder.models import SEMANTIC_REPOSITORY_VERSION


def semantic_repository_to_dict(repo: Any) -> Dict[str, Any]:
    """
    Convert a SemanticRepository instance into a serializable dictionary with versioning tag.
    """
    try:
        data = repo.model_dump(mode="json")
        data["_schema_version"] = SEMANTIC_REPOSITORY_VERSION
        return data
    except Exception as e:
        raise PipelineSerializationError(f"Failed to serialize SemanticRepository to dict: {str(e)}") from e


def dict_to_semantic_repository(data: Dict[str, Any], repo_cls: Any) -> Any:
    """
    Construct a SemanticRepository instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return repo_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise PipelineSerializationError(f"Validation error deserializing SemanticRepository: {str(ve)}") from ve
    except Exception as e:
        raise PipelineSerializationError(f"Failed to deserialize dict to SemanticRepository: {str(e)}") from e


def semantic_repository_to_json(repo: Any, indent: bool = False) -> str:
    """
    Serialize a SemanticRepository instance into a JSON string.
    """
    try:
        data = semantic_repository_to_dict(repo)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise PipelineSerializationError(f"Failed to serialize SemanticRepository to JSON: {str(e)}") from e


def json_to_semantic_repository(json_str: str, repo_cls: Any) -> Any:
    """
    Deserialize a JSON string into a SemanticRepository instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_semantic_repository(data, repo_cls)
    except json.JSONDecodeError as jde:
        raise PipelineSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise PipelineSerializationError(f"Failed to deserialize JSON to SemanticRepository: {str(e)}") from e


def hash_semantic_repository(repo: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a SemanticRepository.
    """
    json_bytes = semantic_repository_to_json(repo).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
