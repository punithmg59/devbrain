"""
models/scope.py
---------------
Phase 4.5 — Language-Independent Scope Resolution Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing lexical
scopes, scope kinds, shadowing relationships, scope trees, scope metrics, and
validation reports.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Zero Engine/Parser Dependencies**: Pure data contracts dependent only on `NodeRange`.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.ast import NodeRange


class ScopeKind(str, Enum):
    """Classification of lexical scope containers."""
    REPOSITORY = "repository"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    LAMBDA = "lambda"
    COMPREHENSION = "comprehension"
    BLOCK = "block"


class ScopeLocation(BaseModel):
    """Source location bounds for a scope block."""
    file_path: str = Field(..., description="Source file path relative to repository root")
    range: Optional[NodeRange] = Field(default=None, description="Source line/column range bounds")


class ShadowingRelationship(BaseModel):
    """Record of a symbol in an inner scope shadowing an outer scope symbol."""
    name: str = Field(..., description="Identifier name being shadowed, e.g. 'x'")
    shadowing_symbol_id: str = Field(..., description="Symbol ID of the inner declaring symbol")
    shadowed_symbol_id: str = Field(..., description="Symbol ID of the outer shadowed symbol")
    inner_scope_id: str = Field(..., description="Scope ID of the inner scope")
    outer_scope_id: str = Field(..., description="Scope ID of the outer scope")


class Scope(BaseModel):
    """Canonical representation of a single lexical scope block."""
    id: str = Field(
        default_factory=lambda: f"scope-{uuid.uuid4().hex[:12]}",
        description="Unique scope identifier",
    )
    name: str = Field(..., description="Descriptive scope name, e.g. 'module:app.auth', 'class:User', 'function:login'")
    kind: ScopeKind = Field(..., description="Lexical scope classification kind")
    parent_id: Optional[str] = Field(default=None, description="Parent scope ID if nested")
    children_ids: List[str] = Field(default_factory=list, description="Child scope IDs nested inside this scope")
    file_path: str = Field(default="", description="Source file path where scope is declared")
    location: Optional[ScopeLocation] = Field(default=None, description="Source location range of scope block")
    defined_symbol_ids: List[str] = Field(default_factory=list, description="IDs of symbols declared directly in this scope")
    visible_symbol_ids: List[str] = Field(default_factory=list, description="IDs of all symbols visible from within this scope")
    shadowed_symbols: List[ShadowingRelationship] = Field(default_factory=list, description="Shadowing relationships originating in this scope")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Scope metadata (nesting depth, enclosing class/func, etc.)")


class ScopeMetrics(BaseModel):
    """Performance telemetry and scope statistics metrics."""
    total_scopes: int = Field(default=0, ge=0, description="Total number of scope nodes in tree")
    scopes_by_kind: Dict[str, int] = Field(default_factory=dict, description="Scope count breakdown by kind")
    max_nesting_depth: int = Field(default=0, ge=0, description="Maximum nesting depth of scope hierarchy")
    total_symbols_defined: int = Field(default=0, ge=0, description="Total symbols defined across all scopes")
    shadowing_count: int = Field(default=0, ge=0, description="Total name shadowing occurrences detected")
    lookup_latency_us: float = Field(default=0.0, ge=0.0, description="Average scope symbol lookup latency in microseconds")
    build_duration_ms: float = Field(default=0.0, ge=0.0, description="Scope tree build duration in milliseconds")
    memory_bytes: int = Field(default=0, ge=0, description="Estimated memory usage in bytes")


class ScopeValidationIssue(BaseModel):
    """Individual issue recorded during ScopeTree validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'CIRCULAR_SCOPE', 'DANGLING_PARENT'")
    message: str = Field(..., description="Human-readable issue explanation")
    scope_id: Optional[str] = Field(default=None, description="Associated scope ID if applicable")


class ScopeValidationReport(BaseModel):
    """Structured validation report for a ScopeTree."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[ScopeValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class ScopeResolutionResult(BaseModel):
    """Output container for scope resolution engine execution."""
    result_id: str = Field(
        default_factory=lambda: f"scoperes-{uuid.uuid4().hex[:12]}",
        description="Unique scope resolution result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    root_scope_ids: List[str] = Field(default_factory=list, description="Root scope IDs (e.g. Repository or Module scopes)")
    scopes: Dict[str, Scope] = Field(default_factory=dict, description="Map of scope_id -> Scope object")
    shadowing_records: List[ShadowingRelationship] = Field(default_factory=list, description="All detected shadowing relationships")
    metrics: ScopeMetrics = Field(default_factory=ScopeMetrics, description="Scope metrics and performance stats")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings recorded during scope resolution")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during scope resolution")
