"""
Index Diagnostics Infrastructure for Graph Query Engine.
"""

from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class DiagnosticSeverity(StrEnum):
    """Diagnostic item severity level."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DiagnosticItem(BaseModel):
    """
    Immutable representation of a single index diagnostic finding.
    """
    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Diagnostic error or warning code")
    severity: DiagnosticSeverity = Field(..., description="INFO, WARNING, ERROR, or CRITICAL")
    component: str = Field(..., description="Affected index or infrastructure component")
    message: str = Field(..., description="Human readable diagnostic message")
    recommendation: str = Field(default="", description="Suggested corrective action")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of diagnostic generation",
    )


class IndexDiagnostics(BaseModel):
    """
    Immutable collection of index diagnostic items.
    """
    model_config = ConfigDict(frozen=True)

    items: tuple[DiagnosticItem, ...] = Field(
        default_factory=tuple,
        description="Tuple of diagnostic items",
    )

    @property
    def has_errors(self) -> bool:
        """Returns True if any ERROR or CRITICAL severity item exists."""
        return any(item.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL) for item in self.items)

    @property
    def error_count(self) -> int:
        """Returns total count of ERROR or CRITICAL severity items."""
        return sum(1 for item in self.items if item.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL))

    @property
    def warning_count(self) -> int:
        """Returns total count of WARNING severity items."""
        return sum(1 for item in self.items if item.severity == DiagnosticSeverity.WARNING)


__all__ = [
    "DiagnosticSeverity",
    "DiagnosticItem",
    "IndexDiagnostics",
]
