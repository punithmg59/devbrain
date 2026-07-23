"""
models/symbol.py
----------------
Phase 4.4 — Language-Independent Symbol Table & Symbol Index Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing symbols,
symbol metadata, symbol scope, symbol table containers, symbol index metrics,
and validation reports.

Design Principles
-----------------
- **Language-Independent**: Reusable across Python, TypeScript, Java, Go, C#, Rust, etc.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Deterministic**: Symbol IDs and Fully Qualified Names (FQNs) are strictly reproducible.
- **Zero Parser/Engine Dependencies**: Pure data contracts dependent only on `NodeRange` (from models.ast).
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.ast import NodeRange


class SymbolKind(str, Enum):
    """Classification of declared symbol entities."""
    MODULE = "module"
    PACKAGE = "package"
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    STRUCT = "struct"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    VARIABLE = "variable"
    CONSTANT = "constant"
    PARAMETER = "parameter"
    IMPORT = "import"
    DECORATOR = "decorator"
    TYPE_ALIAS = "type_alias"
    FIELD = "field"


class SymbolScope(str, Enum):
    """Lexical scope level of a symbol declaration."""
    GLOBAL = "global"
    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    LOCAL = "local"


class SymbolVisibility(str, Enum):
    """Access visibility modifier of a symbol."""
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    INTERNAL = "internal"


class SymbolLocation(BaseModel):
    """Source code location for a symbol definition."""
    file_path: str = Field(..., description="Source file path relative to repository root")
    range: Optional[NodeRange] = Field(default=None, description="Source code line/column range")


def generate_symbol_id(repository_id: str, fqn: str, kind: SymbolKind | str) -> str:
    """
    Generate a deterministic SHA-256 symbol ID.

    Parameters
    ----------
    repository_id:
        Identifier of the repository.
    fqn:
        Fully Qualified Name of the symbol.
    kind:
        SymbolKind enum or string value.

    Returns
    -------
    str
        Deterministic symbol identifier string, e.g. "sym-a1b2c3d4e5f6".
    """
    kind_str = kind.value if isinstance(kind, SymbolKind) else str(kind)
    seed = f"{repository_id}::{fqn}::{kind_str}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"sym-{digest}"


class Symbol(BaseModel):
    """Canonical representation of a single code symbol declaration."""
    id: str = Field(..., description="Unique deterministic symbol identifier")
    fqn: str = Field(..., description="Fully Qualified Name, e.g. 'app.auth.AuthService.login'")
    name: str = Field(..., description="Simple symbol name, e.g. 'login'")
    kind: SymbolKind = Field(..., description="Symbol classification kind")
    parent_id: Optional[str] = Field(default=None, description="Parent symbol ID if nested")
    children_ids: List[str] = Field(default_factory=list, description="Child symbol IDs contained in scope")
    file_path: str = Field(..., description="Source file path where symbol is declared")
    location: Optional[SymbolLocation] = Field(default=None, description="Detailed source location")
    scope: SymbolScope = Field(default=SymbolScope.GLOBAL, description="Lexical scope level")
    visibility: SymbolVisibility = Field(default=SymbolVisibility.PUBLIC, description="Visibility classification")
    language: str = Field(default="python", description="Programming language of symbol")
    repository_id: str = Field(default="repo", description="Repository identifier")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific or entity-specific metadata (docstring, type_annotation, modifiers, etc.)"
    )

    def is_child_of(self, parent_symbol_id: str) -> bool:
        """Return True if this symbol is a direct child of parent_symbol_id."""
        return self.parent_id == parent_symbol_id


class SymbolMetrics(BaseModel):
    """Performance telemetry and distribution metrics for a Symbol Table."""
    total_symbols: int = Field(default=0, ge=0, description="Total number of symbols in table")
    symbols_by_kind: Dict[str, int] = Field(default_factory=dict, description="Symbol count breakdown by kind")
    symbols_by_file: Dict[str, int] = Field(default_factory=dict, description="Symbol count breakdown by file path")
    duplicate_count: int = Field(default=0, ge=0, description="Number of duplicate symbol declarations detected")
    lookup_latency_us: float = Field(default=0.0, ge=0.0, description="Average index lookup latency in microseconds")
    build_duration_ms: float = Field(default=0.0, ge=0.0, description="Symbol table build duration in milliseconds")
    memory_bytes: int = Field(default=0, ge=0, description="Estimated memory footprint of symbol table in bytes")


class SymbolValidationIssue(BaseModel):
    """Individual issue recorded during Symbol Table validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'DUPLICATE_ID', 'DANGLING_PARENT'")
    message: str = Field(..., description="Human-readable issue explanation")
    symbol_id: Optional[str] = Field(default=None, description="Associated symbol ID if applicable")
    fqn: Optional[str] = Field(default=None, description="Associated FQN if applicable")


class SymbolValidationReport(BaseModel):
    """Structured report returned by SymbolTableValidator."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[SymbolValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error issues")
    warning_count: int = Field(default=0, ge=0, description="Total warning issues")
