"""
core/dependency_graph/diagnostics.py
------------------------------------
Diagnostic reporting models for Dependency Graph.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from core.namespaces.enums import DiagnosticSeverity


class GraphDiagnostic(BaseModel):
    """Single diagnostic record emitted during graph construction or validation."""
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


class DependencyGraphDiagnostics(BaseModel):
    """Aggregate diagnostic report for DependencyGraph."""
    diagnostics: List[GraphDiagnostic] = Field(
        default_factory=list,
        description="List of recorded diagnostics across pipeline stages"
    )

    model_config = {
        "frozen": True
    }

    @property
    def has_errors(self) -> bool:
        return any(d.severity == DiagnosticSeverity.ERROR for d in self.diagnostics)

    @property
    def errors(self) -> List[GraphDiagnostic]:
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR]

    @property
    def warnings(self) -> List[GraphDiagnostic]:
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.WARNING]

    def add_error(self, message: str, file_path: Optional[str] = None, line: Optional[int] = None, code: Optional[str] = None) -> DependencyGraphDiagnostics:
        diag = GraphDiagnostic(
            message=message,
            severity=DiagnosticSeverity.ERROR,
            file_path=file_path,
            line=line,
            code=code
        )
        return DependencyGraphDiagnostics(diagnostics=self.diagnostics + [diag])

    def add_warning(self, message: str, file_path: Optional[str] = None, line: Optional[int] = None, code: Optional[str] = None) -> DependencyGraphDiagnostics:
        diag = GraphDiagnostic(
            message=message,
            severity=DiagnosticSeverity.WARNING,
            file_path=file_path,
            line=line,
            code=code
        )
        return DependencyGraphDiagnostics(diagnostics=self.diagnostics + [diag])
