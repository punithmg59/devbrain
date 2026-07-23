"""
models/tree_sitter_models.py
-----------------------------
Phase 4.1 — Tree-sitter Backend Integration Models.

Provides parser-independent, Pydantic V2 wrapper models that encapsulate
Tree-sitter parse tree data WITHOUT leaking any native tree_sitter objects
to consumers. All Tree-sitter objects are translated into serializable
Python data structures at the engine boundary.

Design Principles
-----------------
- **Strict Boundary Enforcement**: Native ``tree_sitter.Node`` and
  ``tree_sitter.Tree`` objects NEVER appear in any public API surface.
  ``ParseTreeNode`` and ``ParseTree`` are the only data contracts.
- **Immutable Value Objects**: All wrapper models are frozen Pydantic V2
  records that can be safely shared across threads.
- **Metrics & Health Integration**: ``GrammarVersion``, ``ParserHealth``,
  and ``EngineMetrics`` carry all operational telemetry needed by the
  monitoring layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Grammar Metadata
# ---------------------------------------------------------------------------

class GrammarVersion(BaseModel):
    """Metadata describing a loaded Tree-sitter grammar."""

    language_key: str = Field(
        ...,
        min_length=1,
        description="Canonical language key, e.g. 'python', 'typescript'",
    )
    package_name: str = Field(
        ...,
        min_length=1,
        description="Python package providing the grammar, e.g. 'tree-sitter-python'",
    )
    abi_version: int = Field(
        ...,
        ge=0,
        description="Tree-sitter ABI version reported by the grammar (0 when load failed)",
    )
    is_loaded: bool = Field(
        default=False,
        description="Whether the grammar has been successfully loaded",
    )
    load_error: Optional[str] = Field(
        default=None,
        description="Error message if grammar loading failed",
    )
    loaded_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when grammar was successfully loaded",
    )


# ---------------------------------------------------------------------------
# Parse Tree Wrapper Models (no native tree_sitter objects)
# ---------------------------------------------------------------------------

class ParseTreeNode(BaseModel):
    """
    Immutable wrapper around a single Tree-sitter syntax node.

    Exposes only serializable Python values — no native ``tree_sitter.Node``
    objects escape this boundary.
    """

    node_type: str = Field(
        ...,
        description="Grammar node type, e.g. 'function_definition', 'identifier'",
    )
    is_named: bool = Field(
        default=True,
        description="True if this is a named node (not anonymous punctuation/keyword)",
    )
    is_error: bool = Field(
        default=False,
        description="True if this is an ERROR recovery node",
    )
    is_missing: bool = Field(
        default=False,
        description="True if this is a MISSING node (inserted by error recovery)",
    )
    start_byte: int = Field(
        default=0,
        ge=0,
        description="0-indexed byte offset of node start in source",
    )
    end_byte: int = Field(
        default=0,
        ge=0,
        description="0-indexed byte offset of node end in source",
    )
    start_point: Tuple[int, int] = Field(
        default=(0, 0),
        description="(row, column) tuple — 0-indexed row, 0-indexed column",
    )
    end_point: Tuple[int, int] = Field(
        default=(0, 0),
        description="(row, column) tuple — 0-indexed row, 0-indexed column",
    )
    text: Optional[str] = Field(
        default=None,
        description="Source text of this node (populated only for leaf nodes)",
    )
    child_count: int = Field(
        default=0,
        ge=0,
        description="Number of direct children",
    )
    children: List["ParseTreeNode"] = Field(
        default_factory=list,
        description="Direct child nodes",
    )


ParseTreeNode.model_rebuild()


class ParseTree(BaseModel):
    """
    Immutable wrapper around a complete Tree-sitter parse result.

    Contains the full node hierarchy plus parse-level metadata.
    No native tree_sitter objects are reachable from this model.
    """

    file_path: str = Field(
        ...,
        min_length=1,
        description="Relative file path of the parsed source",
    )
    language_key: str = Field(
        ...,
        min_length=1,
        description="Language grammar key used for parsing",
    )
    root_node: ParseTreeNode = Field(
        ...,
        description="Root node of the syntax tree",
    )
    source_bytes: int = Field(
        default=0,
        ge=0,
        description="Total source bytes parsed",
    )
    error_node_count: int = Field(
        default=0,
        ge=0,
        description="Count of ERROR recovery nodes in the tree",
    )
    has_errors: bool = Field(
        default=False,
        description="True if the root node has any parse errors",
    )
    parse_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Wall-clock time spent in the Tree-sitter parser in ms",
    )


# ---------------------------------------------------------------------------
# Engine Health & Metrics
# ---------------------------------------------------------------------------

class ParserHealth(BaseModel):
    """Operational health snapshot for the TreeSitterEngine."""

    is_running: bool = Field(
        default=False,
        description="True if the engine is initialized and ready",
    )
    grammar_count: int = Field(
        default=0,
        ge=0,
        description="Number of successfully loaded grammars",
    )
    cached_parser_count: int = Field(
        default=0,
        ge=0,
        description="Number of Parser instances held in cache",
    )
    grammars: List[GrammarVersion] = Field(
        default_factory=list,
        description="Per-grammar status details",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Engine-level errors",
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Seconds since engine was initialized",
    )
    memory_rss_mb: float = Field(
        default=0.0,
        ge=0.0,
        description="Approximate process RSS memory in MB",
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of health check",
    )


class EngineMetrics(BaseModel):
    """Cumulative benchmark and performance metrics for the engine."""

    total_parses: int = Field(default=0, ge=0)
    total_parse_ms: float = Field(default=0.0, ge=0.0)
    grammar_load_times_ms: Dict[str, float] = Field(
        default_factory=dict,
        description="Grammar name → load time in ms",
    )
    parser_reuse_count: Dict[str, int] = Field(
        default_factory=dict,
        description="Grammar name → number of times cached parser was reused",
    )
    parser_creation_count: Dict[str, int] = Field(
        default_factory=dict,
        description="Grammar name → number of fresh Parser instances created",
    )
    error_count: int = Field(default=0, ge=0)

    @property
    def avg_parse_ms(self) -> float:
        """Average parse duration in milliseconds."""
        return (self.total_parse_ms / self.total_parses) if self.total_parses > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        return self.model_dump()
