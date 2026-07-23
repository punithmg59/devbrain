"""
models/reference_models.py
---------------------------
Phase 4.7 — Language-Independent Reference Resolution Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing identifier
usage references, reference kinds, access modes (read/write/call/definition/attribute),
reference indices, reference metrics, and validation reports.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Zero AST/Parser Dependencies**: Pure data contracts.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReferenceKind(str, Enum):
    """Classification of identifier usage reference types."""
    VARIABLE_READ = "variable_read"           # e.g. print(x)
    VARIABLE_WRITE = "variable_write"         # e.g. x = 10
    VARIABLE_READ_WRITE = "variable_rw"       # e.g. x += 1
    FUNCTION_CALL = "function_call"           # e.g. login()
    METHOD_CALL = "method_call"               # e.g. service.login()
    CONSTRUCTOR_CALL = "constructor_call"     # e.g. User()
    TYPE_ANNOTATION = "type_annotation"       # e.g. x: int
    CLASS_DEFINITION = "class_def"            # e.g. class User:
    FUNCTION_DEFINITION = "function_def"      # e.g. def login():
    VARIABLE_DEFINITION = "variable_def"      # e.g. x = 10 (first declaration)
    ATTRIBUTE_ACCESS = "attribute_access"     # e.g. user.name, self.user
    IMPORT_REFERENCE = "import_ref"           # e.g. from auth import AuthService


class ReferenceLocation(BaseModel):
    """Source location bounds for an identifier usage occurrence."""
    file_path: str = Field(..., description="Source file path relative to repository root")
    line: int = Field(..., ge=1, description="1-indexed line number")
    column: int = Field(..., ge=0, description="0-indexed start column offset")
    end_line: int = Field(..., ge=1, description="1-indexed end line number")
    end_column: int = Field(..., ge=0, description="0-indexed end column offset")


class ReferenceRecord(BaseModel):
    """Canonical representation of an individual identifier reference occurrence."""
    id: str = Field(
        default_factory=lambda: f"ref-{uuid.uuid4().hex[:12]}",
        description="Unique reference occurrence identifier",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    file_path: str = Field(..., description="Source file path relative to repository root")
    symbol_id: Optional[str] = Field(default=None, description="Bound target symbol ID in SymbolTable")
    symbol_name: str = Field(..., description="Identifier name string, e.g. 'UserService', 'x', 'login'")
    kind: ReferenceKind = Field(..., description="Reference occurrence classification kind")
    scope_id: str = Field(..., description="ID of enclosing Lexical Scope where usage occurs")
    line: int = Field(..., ge=1, description="1-indexed start line number")
    column: int = Field(..., ge=0, description="0-indexed start column offset")
    end_line: int = Field(..., ge=1, description="1-indexed end line number")
    end_column: int = Field(..., ge=0, description="0-indexed end column offset")
    is_read: bool = Field(default=False, description="True if identifier value is read")
    is_write: bool = Field(default=False, description="True if identifier value is assigned/modified")
    is_definition: bool = Field(default=False, description="True if reference is a symbol declaration site")
    is_call: bool = Field(default=False, description="True if reference is a function/method call invocation")
    is_attribute_access: bool = Field(default=False, description="True if reference is an attribute dot-access")
    attribute_chain: Optional[List[str]] = Field(default=None, description="Full attribute chain, e.g. ['self', 'user', 'name']")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata (arg_count, receiver_symbol_id, etc.)")


class ReferenceResolution(BaseModel):
    """Canonical representation of a resolved reference binding outcome."""
    reference_id: str = Field(..., description="ID of matching ReferenceRecord")
    symbol_id: Optional[str] = Field(default=None, description="Bound target symbol ID")
    symbol_fqn: Optional[str] = Field(default=None, description="Bound target symbol FQN")
    scope_id: str = Field(..., description="Enclosing scope ID")
    is_resolved: bool = Field(default=False, description="True if successfully bound to a Symbol")
    error_message: Optional[str] = Field(default=None, description="Error message if resolution failed")


class ReferenceMetrics(BaseModel):
    """Performance telemetry and reference occurrence statistics."""
    total_references: int = Field(default=0, ge=0, description="Total identifier reference occurrences")
    resolved_count: int = Field(default=0, ge=0, description="Total references resolved to Symbol IDs")
    unresolved_count: int = Field(default=0, ge=0, description="Total unresolved references")
    read_count: int = Field(default=0, ge=0, description="Total read references")
    write_count: int = Field(default=0, ge=0, description="Total write references")
    call_count: int = Field(default=0, ge=0, description="Total call invocation references")
    attribute_count: int = Field(default=0, ge=0, description="Total attribute access references")
    definition_count: int = Field(default=0, ge=0, description="Total definition site references")
    resolution_latency_us: float = Field(default=0.0, ge=0.0, description="Average reference resolution latency in microseconds")
    build_duration_ms: float = Field(default=0.0, ge=0.0, description="Reference resolution build duration in milliseconds")
    memory_bytes: int = Field(default=0, ge=0, description="Estimated memory usage in bytes")


class ReferenceValidationIssue(BaseModel):
    """Individual issue recorded during ReferenceResolution validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'UNRESOLVED_REFERENCE', 'DANGLING_SYMBOL_ID'")
    message: str = Field(..., description="Human-readable issue explanation")
    reference_id: Optional[str] = Field(default=None, description="Associated reference ID if applicable")
    file_path: Optional[str] = Field(default=None, description="Source file path where issue occurred")


class ReferenceValidationReport(BaseModel):
    """Structured validation report for reference resolution."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[ReferenceValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class ReferenceResolutionResult(BaseModel):
    """Output container for reference resolution engine execution."""
    result_id: str = Field(
        default_factory=lambda: f"refres-{uuid.uuid4().hex[:12]}",
        description="Unique reference resolution result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    references: Dict[str, ReferenceRecord] = Field(
        default_factory=dict,
        description="Map of reference_id -> ReferenceRecord object",
    )
    resolutions: Dict[str, ReferenceResolution] = Field(
        default_factory=dict,
        description="Map of reference_id -> ReferenceResolution object",
    )
    metrics: ReferenceMetrics = Field(default_factory=ReferenceMetrics, description="Reference metrics and performance stats")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings recorded during reference resolution")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during reference resolution")
