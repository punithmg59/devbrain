"""
core/facade/serialization.py
-----------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for RepositoryAnalysisResult.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.facade.exceptions import FacadeSerializationError

ANALYSIS_RESULT_VERSION = "4.8.0"


def analysis_result_to_dict(result: Any) -> Dict[str, Any]:
    """
    Convert a RepositoryAnalysisResult instance into a serializable dictionary with versioning tag.
    """
    try:
        data = result.model_dump(mode="json")
        data["_schema_version"] = ANALYSIS_RESULT_VERSION
        return data
    except Exception as e:
        raise FacadeSerializationError(f"Failed to serialize RepositoryAnalysisResult to dict: {str(e)}") from e


def dict_to_analysis_result(data: Dict[str, Any], result_cls: Any) -> Any:
    """
    Construct a RepositoryAnalysisResult instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return result_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise FacadeSerializationError(f"Validation error deserializing RepositoryAnalysisResult: {str(ve)}") from ve
    except Exception as e:
        raise FacadeSerializationError(f"Failed to deserialize dict to RepositoryAnalysisResult: {str(e)}") from e


def analysis_result_to_json(result: Any, indent: bool = False) -> str:
    """
    Serialize a RepositoryAnalysisResult instance into a JSON string.
    """
    try:
        data = analysis_result_to_dict(result)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise FacadeSerializationError(f"Failed to serialize RepositoryAnalysisResult to JSON: {str(e)}") from e


def json_to_analysis_result(json_str: str, result_cls: Any) -> Any:
    """
    Deserialize a JSON string into a RepositoryAnalysisResult instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_analysis_result(data, result_cls)
    except json.JSONDecodeError as jde:
        raise FacadeSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise FacadeSerializationError(f"Failed to deserialize JSON to RepositoryAnalysisResult: {str(e)}") from e


def hash_analysis_result(result: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a RepositoryAnalysisResult.
    """
    json_bytes = analysis_result_to_json(result).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
