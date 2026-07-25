"""
core/namespaces/diagnostics.py
------------------------------
Diagnostics model and error reporting for Namespace Construction.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from core.namespaces.enums import DiagnosticSeverity


class NamespaceDiagnostic(BaseModel):
    """
    Single diagnostic record emitted during namespace building.
    """
    message: str = Field(..., description="Human-readable diagnostic description")
    severity: DiagnosticSeverity = Field(
        default=DiagnosticSeverity.WARNING,
        description="Diagnostic severity level"
    )
    file_path: Optional[str] = Field(default=None, description="Associated file path if applicable")
    line: Optional[int] = Field(default=None, description="1-indexed line number")
    column: Optional[int] = Field(default=None, description="0-indexed column offset")
    code: Optional[str] = Field(default=None, description="Diagnostic error code identifier")

    model_config = {
        "frozen": True
    }


class NamespaceDiagnostics(BaseModel):
    """
    Aggregate diagnostic report containing errors, warnings, and informational records.
    """
    diagnostics: List[NamespaceDiagnostic] = Field(
        default_factory=list,
        description="List of recorded diagnostics"
    )

    model_config = {
        "frozen": True
    }

    @property
    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)

    @property
    def errors(self) -> List[NamespaceDiagnostic]:
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR]

    @property
    def warnings(self) -> List[NamespaceDiagnostic]:
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.WARNING]

    def add_error(self, message: str, file_path: Optional[str] = None, line: Optional[int] = None, code: Optional[str] = None) -> NamespaceDiagnostics:
        diag = NamespaceDiagnostic(
            message=message,
            severity=DiagnosticSeverity.ERROR,
            file_path=file_path,
            line=line,
            code=code
        )
        return NamespaceDiagnostics(diagnostics=self.diagnostics + [diag])

    def add_warning(self, message: str, file_path: Optional[str] = None, line: Optional[int] = None, code: Optional[str] = None) -> NamespaceDiagnostics:
        diag = NamespaceDiagnostic(
            message=message,
            severity=DiagnosticSeverity.WARNING,
            file_path=file_path,
            line=line,
            code=code
        )
        return NamespaceDiagnostics(diagnostics=self.diagnostics + [diag])
