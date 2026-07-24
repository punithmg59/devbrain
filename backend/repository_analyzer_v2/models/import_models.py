"""
models/import_models.py
------------------------
Phase 4.6 — Language-Independent Import Resolution Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing import
records, resolution statuses, aliases, cross-file symbol bindings, metrics, and
import validation reports.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Zero AST/Parser Dependencies**: Pure data contracts dependent only on `NodeRange`.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.ast import NodeRange


class ImportKind(str, Enum):
    """Classification of import statement types."""
    MODULE = "module"                     # e.g. import os, import app.auth
    ALIAS = "alias"                       # e.g. import numpy as np
    FROM_IMPORT = "from_import"           # e.g. from app.auth import AuthService
    FROM_IMPORT_ALIAS = "from_alias"     # e.g. from auth import AuthService as Service
    RELATIVE = "relative"                 # e.g. from .service import UserService
    WILDCARD = "wildcard"                 # e.g. from models import *


class ImportResolutionStatus(str, Enum):
    """Resolution status of an imported module or symbol."""
    RESOLVED_INTERNAL = "resolved_internal"  # Defined inside repository codebase
    RESOLVED_STDLIB = "resolved_stdlib"      # Standard library module (e.g., os, sys)
    RESOLVED_EXTERNAL = "resolved_external"  # Third-party library (e.g., requests, fastapi)
    UNRESOLVED_MODULE = "unresolved_module"  # Module file path not found in repository
    UNRESOLVED_SYMBOL = "unresolved_symbol"  # Target symbol not found inside resolved module
    AMBIGUOUS_MODULE = "ambiguous_module"    # Multiple module path matches found


class ImportAlias(BaseModel):
    """Alias mapping for imported identifiers."""
    original_name: str = Field(..., description="Original declared name, e.g. 'AuthService'")
    alias_name: str = Field(..., description="Alias identifier, e.g. 'Service'")


class ImportRecord(BaseModel):
    """Canonical representation of an individual raw import statement."""
    id: str = Field(
        default_factory=lambda: f"imp-{uuid.uuid4().hex[:12]}",
        description="Unique import statement identifier",
    )
    kind: ImportKind = Field(..., description="Import statement classification kind")
    statement_snippet: str = Field(default="", description="Original import source code snippet")
    source_file_path: str = Field(..., description="Source file path relative to repository root")
    source_module_fqn: str = Field(..., description="Source module FQN, e.g. 'app.services.user'")
    imported_module_name: Optional[str] = Field(default=None, description="Target imported module name, e.g. 'app.auth' or 'os'")
    imported_symbol_name: Optional[str] = Field(default=None, description="Imported symbol name if 'from' import, e.g. 'AuthService'")
    alias: Optional[str] = Field(default=None, description="Import alias name if present, e.g. 'np'")
    relative_level: int = Field(default=0, ge=0, description="Relative dot level: 0 for absolute, 1 for '.', 2 for '..'")
    range: Optional[NodeRange] = Field(default=None, description="Source location range of import statement")
    is_relative: bool = Field(default=False, description="True if relative import")
    is_wildcard: bool = Field(default=False, description="True if wildcard '*' import")


class ImportResolution(BaseModel):
    """Canonical representation of a resolved import mapping."""
    import_id: str = Field(..., description="ID of the matching ImportRecord")
    status: ImportResolutionStatus = Field(..., description="Resolution status outcome")
    target_module_fqn: Optional[str] = Field(default=None, description="Canonical FQN of target resolved module")
    target_file_path: Optional[str] = Field(default=None, description="Repository file path of target resolved module")
    target_symbol_id: Optional[str] = Field(default=None, description="Symbol ID of resolved symbol in SymbolTable")
    target_symbol_fqn: Optional[str] = Field(default=None, description="Fully Qualified Name of target symbol")
    is_stdlib: bool = Field(default=False, description="True if resolved to Python Standard Library")
    is_external: bool = Field(default=False, description="True if resolved to external third-party package")
    wildcard_symbol_ids: List[str] = Field(default_factory=list, description="Symbol IDs expanded from wildcard '*' import")
    error_message: Optional[str] = Field(default=None, description="Error message if resolution failed")


class ImportMetrics(BaseModel):
    """Performance telemetry and statistics for import resolution."""
    total_imports: int = Field(default=0, ge=0, description="Total import statements processed")
    resolved_internal: int = Field(default=0, ge=0, description="Internal repository imports resolved")
    resolved_stdlib: int = Field(default=0, ge=0, description="Standard library imports resolved")
    resolved_external: int = Field(default=0, ge=0, description="Third-party package imports resolved")
    unresolved_count: int = Field(default=0, ge=0, description="Total unresolved imports")
    relative_count: int = Field(default=0, ge=0, description="Total relative imports")
    alias_count: int = Field(default=0, ge=0, description="Total aliased imports")
    wildcard_count: int = Field(default=0, ge=0, description="Total wildcard '*' imports")
    resolution_latency_us: float = Field(default=0.0, ge=0.0, description="Average import resolution latency in microseconds")
    build_duration_ms: float = Field(default=0.0, ge=0.0, description="Import resolution build duration in milliseconds")
    memory_bytes: int = Field(default=0, ge=0, description="Estimated memory usage in bytes")


class ImportValidationIssue(BaseModel):
    """Individual issue recorded during ImportResolution validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'MISSING_MODULE', 'MISSING_SYMBOL', 'CIRCULAR_IMPORT'")
    message: str = Field(..., description="Human-readable issue explanation")
    import_id: Optional[str] = Field(default=None, description="Associated import ID if applicable")
    source_file_path: Optional[str] = Field(default=None, description="Source file path where issue occurred")


class ImportValidationReport(BaseModel):
    """Structured validation report for import resolution."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[ImportValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class ImportResolutionResult(BaseModel):
    """Output container for import resolution engine execution."""
    result_id: str = Field(
        default_factory=lambda: f"impres-{uuid.uuid4().hex[:12]}",
        description="Unique import resolution result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    resolutions: Dict[str, ImportResolution] = Field(
        default_factory=dict,
        description="Map of import_id -> ImportResolution object",
    )
    imports: Dict[str, ImportRecord] = Field(
        default_factory=dict,
        description="Map of import_id -> ImportRecord object",
    )
    metrics: ImportMetrics = Field(default_factory=ImportMetrics, description="Import metrics and performance stats")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings recorded during import resolution")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during import resolution")
