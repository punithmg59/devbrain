"""
models/graph_validation_models.py
---------------------------------
Phase 4.8.3 — Language-Independent Graph Validation Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
validation severity levels, individual validation issues, validation metrics,
structured validation reports, and execution results.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Read-Only Reporting**: Captures issues without mutating target graph entities.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Classification levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Canonical representation of an individual issue detected during graph validation."""
    issue_id: str = Field(
        default_factory=lambda: f"valissue-{uuid.uuid4().hex[:12]}",
        description="Unique issue identifier",
    )
    severity: ValidationSeverity = Field(..., description="Issue severity: INFO, WARNING, ERROR, CRITICAL")
    code: str = Field(..., description="Issue machine-readable code, e.g. 'DUPLICATE_SYMBOL_ID', 'MISSING_FQN'")
    category: str = Field(
        ...,
        description="Validation category: 'StructuralIntegrity', 'Node', 'Edge', 'Index', 'GraphConsistency', 'ReferenceIntegrity'",
    )
    message: str = Field(..., description="Human-readable issue explanation")
    target_id: Optional[str] = Field(default=None, description="Associated symbol_id, edge_id, or key if applicable")
    location: Optional[str] = Field(default=None, description="Source file path or line location string if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for arbitrary issue details")


class ValidationMetrics(BaseModel):
    """Performance telemetry and issue breakdown metrics for graph validation."""
    validated_nodes: int = Field(default=0, ge=0, description="Total nodes inspected")
    validated_edges: int = Field(default=0, ge=0, description="Total edges inspected")
    validated_indexes: int = Field(default=0, ge=0, description="Total index entries inspected")
    rules_executed: int = Field(default=0, ge=0, description="Total validation rule passes executed")
    info_count: int = Field(default=0, ge=0, description="Count of INFO severity issues")
    warning_count: int = Field(default=0, ge=0, description="Count of WARNING severity issues")
    error_count: int = Field(default=0, ge=0, description="Count of ERROR severity issues")
    critical_count: int = Field(default=0, ge=0, description="Count of CRITICAL severity issues")
    validation_duration_ms: float = Field(default=0.0, ge=0.0, description="Validation duration in milliseconds")


class ValidationReport(BaseModel):
    """Structured report aggregating all validation issues and telemetry metrics."""
    is_valid: bool = Field(default=True, description="True if error_count == 0 and critical_count == 0")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of all detected ValidationIssue objects")
    metrics: ValidationMetrics = Field(default_factory=ValidationMetrics, description="Validation telemetry metrics")
    error_count: int = Field(default=0, ge=0, description="Total ERROR severity issues")
    warning_count: int = Field(default=0, ge=0, description="Total WARNING severity issues")
    critical_count: int = Field(default=0, ge=0, description="Total CRITICAL severity issues")


class GraphValidationResult(BaseModel):
    """Output container returned by GraphValidator execution."""
    result_id: str = Field(
        default_factory=lambda: f"valres-{uuid.uuid4().hex[:12]}",
        description="Unique graph validation result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    validation_report: ValidationReport = Field(
        default_factory=ValidationReport,
        description="Aggregated ValidationReport object",
    )
    metrics: ValidationMetrics = Field(
        default_factory=ValidationMetrics,
        description="Validation telemetry metrics",
    )
    warnings: List[str] = Field(default_factory=list, description="Human-readable warning messages")
    errors: List[str] = Field(default_factory=list, description="Human-readable error messages")
