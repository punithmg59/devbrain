"""
models/re_export_models.py
--------------------------
Phase 4.7.1 — Re-Export Symbol Resolution Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
package re-export records, resolution outcomes, metrics, and validation reports
for the Re-Export Symbol Resolution Engine.

Design Principles
-----------------
- **Language-Independent**: Applicable to any Python package that uses __init__.py
  re-export patterns.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (model_dump(), model_dump_json()).
- **Zero AST/Parser Dependencies**: Pure data contracts with no parser coupling.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExportType(str, Enum):
    """Classification of the re-export pattern that produced this export record."""
    FROM_IMPORT = "from_import"           # from .module import Name
    FROM_IMPORT_ALIAS = "from_alias"     # from .module import Name as Alias
    STAR_EXPORT = "star_export"          # from .module import *
    ALL_LIST = "all_list"                # __all__ = ["Name", ...]
    ALL_AUGMENTED = "all_augmented"      # __all__ += ["Name", ...]
    ALL_APPEND = "all_append"            # __all__.append("Name")


class ExportVisibility(str, Enum):
    """Public/private classification of an exported symbol."""
    PUBLIC = "public"    # Does not start with underscore
    PRIVATE = "private"  # Starts with underscore


class ExportRecord(BaseModel):
    """
    Canonical representation of a single package-level re-export declaration.

    An ExportRecord describes a mapping from a package's public interface (the
    exported_name visible to importers) to the originating symbol defined in a
    target internal module (target_fqn).
    """
    export_id: str = Field(
        default_factory=lambda: f"exp-{uuid.uuid4().hex[:12]}",
        description="Unique export record identifier",
    )
    package_fqn: str = Field(
        ...,
        description="FQN of the package that declares this re-export (the __init__.py module), e.g. 'fastapi'",
    )
    package_file_path: str = Field(
        ...,
        description="File path of the __init__.py that declares this re-export, e.g. 'fastapi/__init__.py'",
    )
    exported_name: str = Field(
        ...,
        description="The public name under which the symbol is exported, e.g. 'FastAPI'. For star exports, '*'.",
    )
    original_name: str = Field(
        ...,
        description="Original symbol name in the source module before aliasing, e.g. 'FastAPI'",
    )
    alias: Optional[str] = Field(
        default=None,
        description="Alias if re-exported with 'as' clause, e.g. 'Router' in 'from .routing import APIRouter as Router'",
    )
    source_module_fqn: Optional[str] = Field(
        default=None,
        description="FQN of the module where the symbol originates, e.g. 'fastapi.applications'",
    )
    target_symbol_id: Optional[str] = Field(
        default=None,
        description="Resolved Symbol ID in the SymbolTable after resolution, None before resolution",
    )
    target_fqn: Optional[str] = Field(
        default=None,
        description="Resolved FQN of the target symbol after resolution, e.g. 'fastapi.applications.FastAPI'",
    )
    export_type: ExportType = Field(
        ...,
        description="Classification of the export pattern",
    )
    visibility: ExportVisibility = Field(
        default=ExportVisibility.PUBLIC,
        description="Public or private visibility classification",
    )
    is_star_export: bool = Field(
        default=False,
        description="True if this export was produced by a wildcard 'from module import *' declaration",
    )
    is_resolved: bool = Field(
        default=False,
        description="True after the resolver has linked this export to a target Symbol ID",
    )


class ReExportMetrics(BaseModel):
    """Performance telemetry and statistics for the re-export resolution phase."""
    total_packages_scanned: int = Field(default=0, ge=0, description="Total __init__.py files scanned")
    total_exports_found: int = Field(default=0, ge=0, description="Total ExportRecord objects built")
    total_exports_resolved: int = Field(default=0, ge=0, description="Exports successfully linked to a Symbol ID")
    total_exports_failed: int = Field(default=0, ge=0, description="Exports that could not be linked to a Symbol ID")
    star_exports: int = Field(default=0, ge=0, description="Wildcard star export count")
    all_list_exports: int = Field(default=0, ge=0, description="__all__ list export count")
    alias_exports: int = Field(default=0, ge=0, description="Aliased re-export count")
    max_chain_depth: int = Field(default=0, ge=0, description="Maximum recursion depth reached during resolution")
    build_duration_ms: float = Field(default=0.0, ge=0.0, description="Total build + resolution duration in milliseconds")
    memory_bytes: int = Field(default=0, ge=0, description="Estimated memory footprint in bytes")


class ReExportValidationIssue(BaseModel):
    """Individual issue recorded during re-export validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'DANGLING_EXPORT', 'DUPLICATE_EXPORT', 'CYCLIC_EXPORT'")
    message: str = Field(..., description="Human-readable issue explanation")
    export_id: Optional[str] = Field(default=None, description="Associated ExportRecord ID if applicable")
    package_fqn: Optional[str] = Field(default=None, description="Package FQN where the issue was detected")


class ReExportValidationReport(BaseModel):
    """Structured validation report for re-export resolution."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[ReExportValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class ReExportResolutionResult(BaseModel):
    """Output container for the re-export resolution engine execution."""
    result_id: str = Field(
        default_factory=lambda: f"reexp-{uuid.uuid4().hex[:12]}",
        description="Unique re-export resolution result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    exports: Dict[str, ExportRecord] = Field(
        default_factory=dict,
        description="Map of export_id -> ExportRecord",
    )
    package_export_index: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of package_fqn -> list of export_ids in that package",
    )
    metrics: ReExportMetrics = Field(
        default_factory=ReExportMetrics,
        description="Re-export resolution metrics and telemetry",
    )
    validation_report: ReExportValidationReport = Field(
        default_factory=ReExportValidationReport,
        description="Validation report for the re-export index",
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings during re-export resolution")
    errors: List[str] = Field(default_factory=list, description="Error records during re-export resolution")
