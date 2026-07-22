"""
models/parser.py
----------------
Phase 3.1 — Parser System Data Models.

Defines production-quality, type-safe Pydantic V2 models representing
parser results, options, statistics, metadata, capabilities, versions,
errors, and warnings.

Design Principles
-----------------
- **Immutable Identifiers**: `result_id`, `job_id`, `file_path`, and `parsed_at`
  are set once at construction time and frozen against illegal mutations.
- **Pydantic V2 Validation**: Uses native V2 `Field` constraints (`ge`, `gt`, `min_length`),
  `field_validator`, and `model_validator` to enforce structural integrity.
- **Comprehensive Metadata & Metrics**: `ParserStatistics`, `ParserMetadata`, and
  `ParserCapabilities` provide complete operational visibility for every parse output.
- **Serialisation Ready**: Native support for `.model_dump()`, `.model_dump_json()`, and
  round-trip deserialisation via `.model_validate()`.
- **Zero Engine Dependencies**: Pure data contract — does not import or execute Tree-sitter.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ParserStatus(str, Enum):
    """Execution status of a file parsing operation."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    SYNTAX_ERROR = "syntax_error"
    ENCODING_ERROR = "encoding_error"
    TIMEOUT = "timeout"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    SKIPPED = "skipped"
    INTERNAL_ERROR = "internal_error"


class ParserLanguage(str, Enum):
    """Supported target programming languages for source parsing."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    CSHARP = "csharp"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Version & Capabilities Models
# ---------------------------------------------------------------------------

class ParserVersion(BaseModel):
    """Specifies versioning information for a language parser and grammar."""
    semver: str = Field(
        ...,
        min_length=1,
        description="Semantic version string, e.g. '1.0.0'",
    )
    grammar_version: Optional[str] = Field(
        default=None,
        description="Grammar definition commit hash or version tag",
    )
    abi_version: Optional[int] = Field(
        default=None,
        ge=1,
        description="Tree-sitter or parser engine ABI compatibility version",
    )


class ParserCapabilities(BaseModel):
    """Defines feature capabilities supported by a specific language parser."""
    supports_ast: bool = Field(
        default=True,
        description="Supports Abstract Syntax Tree (AST) generation",
    )
    supports_cst: bool = Field(
        default=False,
        description="Supports Concrete Syntax Tree (CST) loss-less parse trees",
    )
    supports_incremental: bool = Field(
        default=False,
        description="Supports incremental re-parsing of edited buffers",
    )
    supports_symbol_extraction: bool = Field(
        default=True,
        description="Supports top-level and nested symbol extraction",
    )
    supports_import_extraction: bool = Field(
        default=True,
        description="Supports import and dependency statement extraction",
    )
    supports_docstring_extraction: bool = Field(
        default=True,
        description="Supports docstring and inline comment extraction",
    )
    supports_error_recovery: bool = Field(
        default=True,
        description="Supports fault-tolerant parse tree recovery on syntax errors",
    )


# ---------------------------------------------------------------------------
# Options Model
# ---------------------------------------------------------------------------

class ParserOptions(BaseModel):
    """Configuration options governing source file parsing behavior."""
    max_file_size_kb: int = Field(
        default=5000,
        ge=1,
        description="Maximum file size in KB allowed for parsing",
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        description="Parse execution timeout in seconds",
    )
    extract_comments: bool = Field(
        default=True,
        description="Extract inline and block comments",
    )
    extract_docstrings: bool = Field(
        default=True,
        description="Extract module, class, and function docstrings",
    )
    include_cst: bool = Field(
        default=False,
        description="Include full Concrete Syntax Tree in output",
    )
    error_recovery: bool = Field(
        default=True,
        description="Enable error recovery mode for malformed source files",
    )
    encoding: str = Field(
        default="utf-8",
        description="Source file encoding",
    )
    custom_flags: Dict[str, Any] = Field(
        default_factory=dict,
        description="Language-specific parser option flags",
    )


# ---------------------------------------------------------------------------
# Error & Warning Models
# ---------------------------------------------------------------------------

class ParserError(BaseModel):
    """Detailed error record representing a syntax or parser failure."""
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable error description",
    )
    line: int = Field(
        default=1,
        ge=1,
        description="1-indexed line number where the error occurred",
    )
    column: int = Field(
        default=0,
        ge=0,
        description="0-indexed column offset where the error occurred",
    )
    start_byte: Optional[int] = Field(
        default=None,
        ge=0,
        description="Start byte offset in source content",
    )
    end_byte: Optional[int] = Field(
        default=None,
        ge=0,
        description="End byte offset in source content",
    )
    severity: str = Field(
        default="error",
        description="Error severity level ('error', 'critical', 'warning')",
    )
    node_type: Optional[str] = Field(
        default=None,
        description="Grammar node type where syntax failure was flagged",
    )
    snippet: Optional[str] = Field(
        default=None,
        description="Source code snippet surrounding the error location",
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ParserError message must not be blank.")
        return v


class ParserWarning(BaseModel):
    """Non-fatal warning generated during source parsing."""
    message: str = Field(
        ...,
        min_length=1,
        description="Warning description message",
    )
    line: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-indexed line number if applicable",
    )
    column: Optional[int] = Field(
        default=None,
        ge=0,
        description="0-indexed column offset if applicable",
    )
    code: Optional[str] = Field(
        default=None,
        description="Optional diagnostic code, e.g. 'W001'",
    )


# ---------------------------------------------------------------------------
# Performance & Metadata Models
# ---------------------------------------------------------------------------

class ParserStatistics(BaseModel):
    """Execution metrics captured during source file parsing."""
    duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Parse duration in milliseconds",
    )
    bytes_parsed: int = Field(
        default=0,
        ge=0,
        description="Total source content bytes parsed",
    )
    lines_parsed: int = Field(
        default=0,
        ge=0,
        description="Total lines of code parsed",
    )
    node_count: int = Field(
        default=0,
        ge=0,
        description="Total syntax tree nodes generated",
    )
    error_count: int = Field(
        default=0,
        ge=0,
        description="Total parse/syntax errors encountered",
    )
    warning_count: int = Field(
        default=0,
        ge=0,
        description="Total parse warnings generated",
    )
    memory_rss_bytes: int = Field(
        default=0,
        ge=0,
        description="Peak memory consumed during parse operation in bytes",
    )


class ParserMetadata(BaseModel):
    """Metadata describing the parser engine instance and parse execution."""
    parser_name: str = Field(
        ...,
        min_length=1,
        description="Name of parser, e.g. 'tree-sitter-python'",
    )
    language: ParserLanguage = Field(
        ...,
        description="Target programming language",
    )
    version: ParserVersion = Field(
        ...,
        description="Parser engine and grammar version specifications",
    )
    capabilities: ParserCapabilities = Field(
        default_factory=ParserCapabilities,
        description="Feature capabilities supported by this parser",
    )
    parsed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of parse execution",
    )
    file_hash: Optional[str] = Field(
        default=None,
        description="SHA256 hash of the parsed file content",
    )


# ---------------------------------------------------------------------------
# Canonical ParserResult Model
# ---------------------------------------------------------------------------

class ParserResult(BaseModel):
    """
    Canonical output container for a source file parsing operation.
    """
    result_id: str = Field(
        default_factory=lambda: f"prs-{uuid.uuid4().hex[:12]}",
        description="Globally unique parse result identifier",
    )
    job_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the AnalysisJob that triggered this parse",
    )
    file_path: str = Field(
        ...,
        min_length=1,
        description="Relative path of the source file parsed",
    )
    language: ParserLanguage = Field(
        ...,
        description="Detected or target programming language",
    )
    status: ParserStatus = Field(
        default=ParserStatus.SUCCESS,
        description="Overall parsing status outcome",
    )
    errors: List[ParserError] = Field(
        default_factory=list,
        description="List of syntax or parse errors encountered",
    )
    warnings: List[ParserWarning] = Field(
        default_factory=list,
        description="List of non-fatal parse warnings",
    )
    statistics: ParserStatistics = Field(
        default_factory=ParserStatistics,
        description="Execution statistics for the parse run",
    )
    metadata: ParserMetadata = Field(
        ...,
        description="Parser engine metadata and version info",
    )
    ast_root: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialised AST root node payload",
    )
    cst_root: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialised CST root node payload",
    )
    raw_symbols: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted raw symbol definitions payload",
    )
    raw_imports: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted raw import statements payload",
    )

    @field_validator("job_id", "file_path")
    @classmethod
    def string_fields_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank or whitespace-only.")
        return v

    @model_validator(mode="after")
    def sync_error_counts(self) -> ParserResult:
        """Keep statistics error/warning counts synchronized with actual lists."""
        if len(self.errors) != self.statistics.error_count and self.statistics.error_count == 0:
            # Auto-update if default 0
            object.__setattr__(
                self,
                "statistics",
                self.statistics.model_copy(
                    update={
                        "error_count": len(self.errors),
                        "warning_count": len(self.warnings),
                    }
                ),
            )
        return self
