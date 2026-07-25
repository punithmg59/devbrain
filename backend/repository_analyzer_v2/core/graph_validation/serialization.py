"""
core/graph_validation/serialization.py
---------------------------------------
Serialization, Deserialization, Hashing, and Schema Versioning for DependencyGraphValidationReport.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict
from pydantic import ValidationError

from core.graph_validation.exceptions import ValidationSerializationError

VALIDATION_REPORT_VERSION = "4.7.0"


def validation_report_to_dict(report: Any) -> Dict[str, Any]:
    """
    Convert a DependencyGraphValidationReport instance into a serializable dictionary with versioning tag.
    """
    try:
        data = report.model_dump(mode="json")
        data["_schema_version"] = VALIDATION_REPORT_VERSION
        return data
    except Exception as e:
        raise ValidationSerializationError(f"Failed to serialize DependencyGraphValidationReport to dict: {str(e)}") from e


def dict_to_validation_report(data: Dict[str, Any], report_cls: Any) -> Any:
    """
    Construct a DependencyGraphValidationReport instance from a dictionary.
    """
    try:
        clean_data = dict(data)
        clean_data.pop("_schema_version", None)
        return report_cls.model_validate(clean_data)
    except ValidationError as ve:
        raise ValidationSerializationError(f"Validation error deserializing DependencyGraphValidationReport: {str(ve)}") from ve
    except Exception as e:
        raise ValidationSerializationError(f"Failed to deserialize dict to DependencyGraphValidationReport: {str(e)}") from e


def validation_report_to_json(report: Any, indent: bool = False) -> str:
    """
    Serialize a DependencyGraphValidationReport instance into a JSON string.
    """
    try:
        data = validation_report_to_dict(report)
        return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)
    except Exception as e:
        raise ValidationSerializationError(f"Failed to serialize DependencyGraphValidationReport to JSON: {str(e)}") from e


def json_to_validation_report(json_str: str, report_cls: Any) -> Any:
    """
    Deserialize a JSON string into a DependencyGraphValidationReport instance.
    """
    try:
        data = json.loads(json_str)
        return dict_to_validation_report(data, report_cls)
    except json.JSONDecodeError as jde:
        raise ValidationSerializationError(f"Invalid JSON string format: {str(jde)}") from jde
    except Exception as e:
        raise ValidationSerializationError(f"Failed to deserialize JSON to DependencyGraphValidationReport: {str(e)}") from e


def hash_validation_report(report: Any) -> str:
    """
    Compute a deterministic cryptographic SHA-256 hash of a DependencyGraphValidationReport.
    """
    json_bytes = validation_report_to_json(report).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
