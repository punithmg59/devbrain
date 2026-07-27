"""
Query Diagnostics and Source Position Tracking Models.
"""

from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class SourceLocation(BaseModel):
    """
    Immutable position model tracking exact source file location for query elements.
    """
    model_config = ConfigDict(frozen=True)

    file_path: Optional[str] = Field(default=None, description="Source file path if applicable")
    start_line: Optional[int] = Field(default=None, description="1-indexed starting line number")
    start_column: Optional[int] = Field(default=None, description="1-indexed starting column number")
    end_line: Optional[int] = Field(default=None, description="1-indexed ending line number")
    end_column: Optional[int] = Field(default=None, description="1-indexed ending column number")
    span_offset: Optional[int] = Field(default=None, description="Byte offset in source string")

    def __str__(self) -> str:
        if self.file_path and self.start_line is not None:
            col_str = f":{self.start_column}" if self.start_column is not None else ""
            return f"{self.file_path}:{self.start_line}{col_str}"
        return "<unknown_location>"


class QueryDiagnosticItem(BaseModel):
    """
    Immutable warning or diagnostic metadata attached to a query AST node or query object.
    """
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique diagnostic rule identifier")
    severity: str = Field(default="WARNING", description="Severity level: INFO, WARNING, ERROR")
    message: str = Field(..., description="Human readable diagnostic message")
    location: Optional[SourceLocation] = Field(default=None, description="Associated source location")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context attributes")


class QueryDiagnosticsMetadata(BaseModel):
    """
    Immutable diagnostics container attached to EngineeringQuery.
    """
    model_config = ConfigDict(frozen=True)

    diagnostics: Tuple[QueryDiagnosticItem, ...] = Field(default_factory=tuple, description="Recorded diagnostic items")
    source_mapping: Dict[str, SourceLocation] = Field(default_factory=dict, description="Map of node IDs to SourceLocation")

    def add_diagnostic(self, item: QueryDiagnosticItem) -> "QueryDiagnosticsMetadata":
        """Returns a new QueryDiagnosticsMetadata with the additional item."""
        return QueryDiagnosticsMetadata(
            diagnostics=self.diagnostics + (item,),
            source_mapping=self.source_mapping,
        )


__all__ = [
    "SourceLocation",
    "QueryDiagnosticItem",
    "QueryDiagnosticsMetadata",
]
