"""
models/diagnostics.py
---------------------
Phase 3.3 — Parser Diagnostics System Data Models.

Defines parser-independent, JSON-serializable diagnostic models (`Diagnostic`,
`DiagnosticCollection`, `DiagnosticSeverity`, `DiagnosticCode`, `Suggestion`).

Design Principles
-----------------
- **Parser-Independent**: Serves as the standard diagnostic contract across any language
  parser, linter, or compiler engine.
- **Categorized Severities**: Supports hints, warnings, syntax errors, recoverable errors,
  and fatal errors.
- **Auto-Fix Suggestions**: `Suggestion` model provides replacement code spans for automated
  quick-fixes and refactorings.
- **Full JSON Serialization**: Native Pydantic V2 `.model_dump_json()` and `.to_json()` helper methods.
- **Immutable Identifiers**: `diagnostic_id`, `collection_id`, and `suggestion_id` generated via UUID v4.
"""

from __future__ import annotations

import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from models.ast import NodeRange


# ---------------------------------------------------------------------------
# Severities & Codes
# ---------------------------------------------------------------------------

class DiagnosticSeverity(str, Enum):
    """Severity classification of a parser diagnostic."""
    HINT = "hint"
    WARNING = "warning"
    SYNTAX_ERROR = "syntax_error"
    RECOVERABLE_ERROR = "recoverable_error"
    FATAL_ERROR = "fatal_error"


class DiagnosticCode(str, Enum):
    """Standardized diagnostic error and classification codes."""
    SYNTAX_UNEXPECTED_TOKEN = "SYNTAX_001"
    SYNTAX_UNTERMINATED_STRING = "SYNTAX_002"
    SYNTAX_MISSING_DELIMITER = "SYNTAX_003"
    SYNTAX_INDENTATION_ERROR = "SYNTAX_004"
    ENCODING_INVALID_UTF8 = "ENCODING_001"
    RECOVERY_NODE_DROPPED = "RECOVERY_001"
    FATAL_PARSE_TIMEOUT = "FATAL_001"
    FATAL_FILE_TOO_LARGE = "FATAL_002"
    UNSUPPORTED_GRAMMAR = "GRAMMAR_001"
    UNKNOWN = "DIAGNOSTIC_999"


# ---------------------------------------------------------------------------
# Suggestion Model
# ---------------------------------------------------------------------------

class Suggestion(BaseModel):
    """Automated quick-fix or refactoring suggestion for a diagnostic."""
    suggestion_id: str = Field(
        default_factory=lambda: f"sug-{uuid.uuid4().hex[:8]}",
        description="Globally unique suggestion identifier",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of suggested fix",
    )
    replacement_text: Optional[str] = Field(
        default=None,
        description="Suggested replacement code text",
    )
    range: Optional[NodeRange] = Field(
        default=None,
        description="Target source code range to be replaced",
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Suggestion description must not be blank.")
        return v


# ---------------------------------------------------------------------------
# Diagnostic Model
# ---------------------------------------------------------------------------

class Diagnostic(BaseModel):
    """Single diagnostic record emitted during parsing or analysis."""
    diagnostic_id: str = Field(
        default_factory=lambda: f"diag-{uuid.uuid4().hex[:12]}",
        description="Globally unique diagnostic identifier",
    )
    severity: DiagnosticSeverity = Field(
        ...,
        description="Severity classification",
    )
    code: Union[DiagnosticCode, str] = Field(
        default=DiagnosticCode.UNKNOWN,
        description="Standardized diagnostic code or string key",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Detailed diagnostic message description",
    )
    file_path: str = Field(
        ...,
        min_length=1,
        description="Relative path of file where diagnostic occurred",
    )
    range: Optional[NodeRange] = Field(
        default=None,
        description="Source code range coordinate where diagnostic occurred",
    )
    suggestions: List[Suggestion] = Field(
        default_factory=list,
        description="Automated remediation or quick-fix suggestions",
    )
    source_parser: Optional[str] = Field(
        default=None,
        description="Parser or tool engine name emitting this diagnostic",
    )
    is_recoverable: bool = Field(
        default=True,
        description="True if parser recovered and continued processing after this diagnostic",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorization tags, e.g. ['syntax', 'deprecated']",
    )

    @field_validator("message", "file_path")
    @classmethod
    def string_fields_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank.")
        return v


# ---------------------------------------------------------------------------
# DiagnosticCollection Model
# ---------------------------------------------------------------------------

class DiagnosticCollection(BaseModel):
    """Collection container for diagnostics belonging to a single file or run."""
    collection_id: str = Field(
        default_factory=lambda: f"dcol-{uuid.uuid4().hex[:12]}",
        description="Globally unique diagnostic collection identifier",
    )
    file_path: str = Field(
        ...,
        min_length=1,
        description="Relative file path associated with these diagnostics",
    )
    diagnostics: List[Diagnostic] = Field(
        default_factory=list,
        description="List of diagnostic items",
    )

    @field_validator("file_path")
    @classmethod
    def file_path_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("file_path must not be blank.")
        return v

    @property
    def has_errors(self) -> bool:
        """True if collection contains any syntax, recoverable, or fatal errors."""
        return any(
            d.severity in {
                DiagnosticSeverity.SYNTAX_ERROR,
                DiagnosticSeverity.RECOVERABLE_ERROR,
                DiagnosticSeverity.FATAL_ERROR,
            }
            for d in self.diagnostics
        )

    @property
    def has_fatal_errors(self) -> bool:
        """True if collection contains any fatal errors."""
        return any(d.severity == DiagnosticSeverity.FATAL_ERROR for d in self.diagnostics)

    @property
    def has_warnings(self) -> bool:
        """True if collection contains any warnings."""
        return any(d.severity == DiagnosticSeverity.WARNING for d in self.diagnostics)

    def get_by_severity(self, severity: DiagnosticSeverity) -> List[Diagnostic]:
        """Return all diagnostics matching `severity`."""
        return [d for d in self.diagnostics if d.severity == severity]

    def add_diagnostic(self, diagnostic: Diagnostic) -> None:
        """Add a diagnostic item to the collection."""
        self.diagnostics.append(diagnostic)

    def add_error(
        self,
        message: str,
        code: Union[DiagnosticCode, str] = DiagnosticCode.SYNTAX_UNEXPECTED_TOKEN,
        range: Optional[NodeRange] = None,
        is_fatal: bool = False,
    ) -> Diagnostic:
        """Convenience method to create and append an error diagnostic."""
        severity = DiagnosticSeverity.FATAL_ERROR if is_fatal else DiagnosticSeverity.SYNTAX_ERROR
        diag = Diagnostic(
            severity=severity,
            code=code,
            message=message,
            file_path=self.file_path,
            range=range,
            is_recoverable=not is_fatal,
        )
        self.add_diagnostic(diag)
        return diag

    def add_warning(
        self,
        message: str,
        code: Union[DiagnosticCode, str] = DiagnosticCode.UNKNOWN,
        range: Optional[NodeRange] = None,
    ) -> Diagnostic:
        """Convenience method to create and append a warning diagnostic."""
        diag = Diagnostic(
            severity=DiagnosticSeverity.WARNING,
            code=code,
            message=message,
            file_path=self.file_path,
            range=range,
        )
        self.add_diagnostic(diag)
        return diag

    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to Python dictionary."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Export collection to JSON string."""
        return self.model_dump_json(indent=indent)
