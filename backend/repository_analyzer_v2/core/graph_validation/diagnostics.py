"""
core/graph_validation/diagnostics.py
------------------------------------
Diagnostic reporting models for Dependency Graph Validation Framework.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from core.namespaces.enums import DiagnosticSeverity


class ValidationCategory(str, Enum):
    """Categories of graph validation rules."""
    STRUCTURAL = "structural"
    REFERENCE = "reference"
    INDEX = "index"
    METADATA = "metadata"
    VERSION = "version"
    INTEGRITY = "integrity"
    PERFORMANCE = "performance"


class ValidationDiagnostic(BaseModel):
    """Single diagnostic record emitted during graph validation."""
    message: str = Field(..., description="Human-readable diagnostic description")
    severity: DiagnosticSeverity = Field(
        default=DiagnosticSeverity.WARNING,
        description="Diagnostic severity level"
    )
    category: ValidationCategory = Field(
        default=ValidationCategory.STRUCTURAL,
        description="Validation category classification"
    )
    file_path: Optional[str] = Field(default=None, description="Associated file path if applicable")
    line: Optional[int] = Field(default=None, description="1-indexed line number")
    column: Optional[int] = Field(default=None, description="0-indexed column offset")
    code: Optional[str] = Field(default=None, description="Diagnostic error code identifier")

    model_config = {
        "frozen": True
    }


class ValidationDiagnostics(BaseModel):
    """Aggregate diagnostic report for graph validation."""
    diagnostics: List[ValidationDiagnostic] = Field(
        default_factory=list,
        description="List of recorded validation diagnostics"
    )

    model_config = {
        "frozen": True
    }

    @property
    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)

    @property
    def errors(self) -> List[ValidationDiagnostic]:
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationDiagnostic]:
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.WARNING]

    def add_error(
        self,
        message: str,
        category: ValidationCategory = ValidationCategory.STRUCTURAL,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
        code: Optional[str] = None
    ) -> ValidationDiagnostics:
        diag = ValidationDiagnostic(
            message=message,
            severity=DiagnosticSeverity.ERROR,
            category=category,
            file_path=file_path,
            line=line,
            code=code
        )
        return ValidationDiagnostics(diagnostics=self.diagnostics + [diag])

    def add_warning(
        self,
        message: str,
        category: ValidationCategory = ValidationCategory.STRUCTURAL,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
        code: Optional[str] = None
    ) -> ValidationDiagnostics:
        diag = ValidationDiagnostic(
            message=message,
            severity=DiagnosticSeverity.WARNING,
            category=category,
            file_path=file_path,
            line=line,
            code=code
        )
        return ValidationDiagnostics(diagnostics=self.diagnostics + [diag])
