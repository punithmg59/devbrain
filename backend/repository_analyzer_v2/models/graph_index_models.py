"""
models/graph_index_models.py
----------------------------
Phase 4.8.2 — Language-Independent Call Graph Index Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
fast O(1) graph lookup indexes, query engine containers, index telemetry metrics,
validation reports, and result objects.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Zero Copy**: Stores references to existing `CallGraphNode` and `CallGraphEdge` objects.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.graph_models import CallGraph, CallGraphEdge, CallGraphNode


class GraphIndex(BaseModel):
    """Container holding pre-computed O(1) lookup tables for graph nodes and edges."""
    node_by_symbol_id: Dict[str, CallGraphNode] = Field(
        default_factory=dict,
        description="Index map: symbol_id -> CallGraphNode",
    )
    node_by_fqn: Dict[str, CallGraphNode] = Field(
        default_factory=dict,
        description="Index map: fully_qualified_name -> CallGraphNode",
    )
    nodes_by_file: Dict[str, List[CallGraphNode]] = Field(
        default_factory=dict,
        description="Index map: file_path -> [CallGraphNode]",
    )
    edges_by_caller: Dict[str, List[CallGraphEdge]] = Field(
        default_factory=dict,
        description="Index map: caller_symbol_id -> [outgoing CallGraphEdge]",
    )
    edges_by_callee: Dict[str, List[CallGraphEdge]] = Field(
        default_factory=dict,
        description="Index map: callee_symbol_id -> [incoming CallGraphEdge]",
    )
    edges_by_file: Dict[str, List[CallGraphEdge]] = Field(
        default_factory=dict,
        description="Index map: file_path -> [CallGraphEdge]",
    )
    callers_index: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Lookup map: symbol_id -> [caller_symbol_ids]",
    )
    callees_index: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Lookup map: symbol_id -> [callee_symbol_ids]",
    )


class GraphIndexMetrics(BaseModel):
    """Performance telemetry and index table statistics for graph indexing."""
    indexed_nodes: int = Field(default=0, ge=0, description="Total nodes indexed")
    indexed_edges: int = Field(default=0, ge=0, description="Total edges indexed")
    caller_index_size: int = Field(default=0, ge=0, description="Unique caller entries in callers_index")
    callee_index_size: int = Field(default=0, ge=0, description="Unique callee entries in callees_index")
    file_index_size: int = Field(default=0, ge=0, description="Unique file entries in nodes_by_file")
    fqn_index_size: int = Field(default=0, ge=0, description="Unique FQN entries in node_by_fqn")
    duplicate_index_entries: int = Field(default=0, ge=0, description="Count of duplicate index entries skipped or merged")
    build_time_ms: float = Field(default=0.0, ge=0.0, description="Index construction time in milliseconds")
    peak_memory_mb: float = Field(default=0.0, ge=0.0, description="Peak memory footprint in megabytes")
    lookups_per_second: float = Field(default=0.0, ge=0.0, description="Benchmark O(1) query throughput lookups per second")


class GraphIndexValidationIssue(BaseModel):
    """Individual issue recorded during graph index validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'MISSING_INDEXED_NODE', 'CORRUPTED_FQN_INDEX'")
    message: str = Field(..., description="Human-readable issue explanation")
    key: Optional[str] = Field(default=None, description="Associated index key if applicable")


class GraphIndexValidationReport(BaseModel):
    """Structured validation report for graph index construction."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[GraphIndexValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


from pydantic import BaseModel, ConfigDict, Field


class CallGraphIndexResult(BaseModel):
    """Output container for graph index builder execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    result_id: str = Field(
        default_factory=lambda: f"cgidx-{uuid.uuid4().hex[:12]}",
        description="Unique call graph index result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    graph: CallGraph = Field(default_factory=CallGraph, description="Source CallGraph object")
    graph_index: GraphIndex = Field(default_factory=GraphIndex, description="Pre-computed GraphIndex container")
    query_engine: Optional[Any] = Field(default=None, description="Instantiated CallGraphQueryEngine gateway")
    metrics: GraphIndexMetrics = Field(default_factory=GraphIndexMetrics, description="Graph index telemetry metrics")
    validation_report: GraphIndexValidationReport = Field(
        default_factory=GraphIndexValidationReport,
        description="Index validation report",
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warning messages recorded during indexing")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during indexing")
