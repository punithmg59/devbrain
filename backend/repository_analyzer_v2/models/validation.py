"""
models/validation.py
--------------------
Phase 3.10 — Parser Validation Framework Data Models.

Defines Pydantic V2 models and enums representing validation severity, issue codes,
validation error/warning items, configurable validation requirements, and comprehensive
validation reports.

Design Principles
-----------------
- **Independent Data Contracts**: Zero dependency on parser execution engines.
- **Pydantic V2 Native**: Utilises field constraints, validators, and serialization options.
- **Serializable Reports**: Full support for `.model_dump()`, `.model_dump_json()`, and helper export methods.
- **Rich Contextual Metadata**: Captures field paths, issue codes, context dictionaries, and metrics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from utils.exceptions import ErrorCode, ValidationError


class ValidationIssueSeverity(str, Enum):
    """Severity levels for items flagged during validation."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssueCode(str, Enum):
    """Standardized machine-readable codes for validation issue categories."""
    # General / Schema
    SCHEMA_INVALID = "VAL_SCHEMA_001"
    REQUIRED_FIELD_MISSING = "VAL_SCHEMA_002"
    INVALID_TYPE = "VAL_SCHEMA_003"

    # ParserResult & Status
    STATUS_ERROR_MISMATCH = "VAL_RESULT_001"
    STATUS_AST_MISMATCH = "VAL_RESULT_002"
    STATISTICS_MISMATCH = "VAL_RESULT_003"
    INVALID_FILE_PATH = "VAL_RESULT_004"
    INVALID_JOB_ID = "VAL_RESULT_005"

    # AST & Geometry
    AST_MISSING_ROOT = "VAL_AST_001"
    AST_INVALID_COORDINATES = "VAL_AST_002"
    AST_RANGE_ORDERING = "VAL_AST_003"
    AST_CHILD_RANGE_OUT_OF_BOUNDS = "VAL_AST_004"
    AST_DUPLICATE_NODE_ID = "VAL_AST_005"
    AST_PARENT_CHILD_MISMATCH = "VAL_AST_006"
    AST_METRICS_MISMATCH = "VAL_AST_007"
    AST_CYCLIC_REFERENCE = "VAL_AST_008"

    # Diagnostics
    DIAGNOSTIC_BLANK_MESSAGE = "VAL_DIAG_001"
    DIAGNOSTIC_INVALID_CODE = "VAL_DIAG_002"
    DIAGNOSTIC_INVALID_RANGE = "VAL_DIAG_003"
    DIAGNOSTIC_SUGGESTION_INVALID = "VAL_DIAG_004"

    # Metadata & Version & Capabilities & Language
    METADATA_INVALID_PARSER_NAME = "VAL_META_001"
    METADATA_INVALID_HASH = "VAL_META_002"
    VERSION_INVALID_SEMVER = "VAL_VER_001"
    VERSION_INVALID_ABI = "VAL_VER_002"
    CAPABILITIES_INCONSISTENT = "VAL_CAP_001"
    LANGUAGE_MISMATCH = "VAL_LANG_001"
    LANGUAGE_UNSUPPORTED = "VAL_LANG_002"

    # Operational Requirements
    REQUIREMENT_FAILED = "VAL_REQ_001"
    PARSE_TIMEOUT_EXCEEDED = "VAL_REQ_002"
    DOCSTRING_EXTRACTION_MISSING = "VAL_REQ_003"


class ValidationErrorItem(BaseModel):
    """Record describing a specific validation error."""
    code: ValidationIssueCode = Field(..., description="Machine-readable validation code")
    message: str = Field(..., min_length=1, description="Human-readable description of validation error")
    field_path: Optional[str] = Field(default=None, description="Dot-separated field path where error occurred")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context key-value attributes")

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ValidationErrorItem message must not be blank.")
        return v


class ValidationWarningItem(BaseModel):
    """Record describing a non-fatal validation warning."""
    code: ValidationIssueCode = Field(..., description="Machine-readable validation code")
    message: str = Field(..., min_length=1, description="Human-readable description of warning")
    field_path: Optional[str] = Field(default=None, description="Dot-separated field path")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context key-value attributes")

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ValidationWarningItem message must not be blank.")
        return v


class ValidationRequirements(BaseModel):
    """Configurable operational rules for enforcing strict parse result compliance."""
    allow_syntax_errors: bool = Field(default=True, description="Allow parse results with status SYNTAX_ERROR")
    require_ast: bool = Field(default=True, description="Require valid AST root on successful parse results")
    require_docstrings: bool = Field(default=False, description="Require docstring extraction capabilities")
    max_duration_ms: Optional[float] = Field(default=None, ge=0.0, description="Maximum permitted parse duration in ms")
    allowed_languages: Optional[List[str]] = Field(default=None, description="Allowed language identifiers whitelist")
    min_semver: Optional[str] = Field(default=None, description="Minimum allowed parser version semver")
    strict_parent_links: bool = Field(default=True, description="Enforce strict bidirectional parent-child AST links")
    strict_range_containment: bool = Field(default=True, description="Enforce parent range contains child range")
    custom_rules: Dict[str, Any] = Field(default_factory=dict, description="Extensible rule flags")


class ValidationReport(BaseModel):
    """Comprehensive validation outcome report."""
    is_valid: bool = Field(..., description="True if no validation errors were encountered")
    errors: List[ValidationErrorItem] = Field(default_factory=list, description="Validation error details")
    warnings: List[ValidationWarningItem] = Field(default_factory=list, description="Validation warning details")
    checked_count: int = Field(default=0, ge=0, description="Total validation assertions evaluated")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Time spent performing validation in ms")
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of validation execution",
    )

    @property
    def has_errors(self) -> bool:
        """True if any validation errors are present."""
        return len(self.errors) > 0 or not self.is_valid

    @property
    def error_count(self) -> int:
        """Count of error items."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Count of warning items."""
        return len(self.warnings)

    def raise_if_invalid(self, stage_name: str = "ParserValidation") -> None:
        """
        Raise a domain `ValidationError` if `is_valid` is False.

        Raises
        ------
        ValidationError
            Carries `ErrorCode.VALIDATION_SCHEMA` and formatted message listing errors.
        """
        if not self.is_valid:
            err_msg_summary = "; ".join([f"[{e.code.value}] {e.field_path}: {e.message}" if e.field_path else f"[{e.code.value}] {e.message}" for e in self.errors])
            raise ValidationError(
                message=f"Parser validation failed with {len(self.errors)} error(s): {err_msg_summary}",
                code=ErrorCode.VALIDATION_SCHEMA,
                stage_name=stage_name,
                context={
                    "error_count": len(self.errors),
                    "warning_count": len(self.warnings),
                    "errors": [e.model_dump() for e in self.errors],
                },
            )

    def to_dict(self) -> Dict[str, Any]:
        """Export report as dictionary."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Export report as JSON string."""
        return self.model_dump_json(indent=indent)
