"""
models/graph_models.py
----------------------
Phase 4.8.1 — Language-Independent Call Graph Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
directed call graph nodes, edges, adjacency structures, graph metrics, validation
reports, and execution results.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Zero Parser/Engine Dependencies**: Pure data contracts.
- **Memory-Efficient**: Store symbol IDs and light attributes instead of heavy objects.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CallGraphNode(BaseModel):
    """Canonical representation of a node in the directed call graph."""
    symbol_id: str = Field(..., description="Unique node identifier matching SymbolId in SymbolTable or external ID")
    fully_qualified_name: str = Field(..., description="Fully qualified name, e.g. 'fastapi.applications.FastAPI'")
    name: str = Field(..., description="Simple symbol identifier name, e.g. 'FastAPI'")
    node_type: str = Field(default="function", description="Node kind, e.g. 'function', 'method', 'class', 'constructor', 'external'")
    file_path: str = Field(default="", description="Source file path relative to repository root")
    line: int = Field(default=1, ge=1, description="1-indexed line number of symbol definition")
    column: int = Field(default=0, ge=0, description="0-indexed column offset of symbol definition")
    is_external: bool = Field(default=False, description="True if node represents stdlib or third-party external symbol")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for arbitrary node properties")


class CallGraphEdge(BaseModel):
    """Canonical representation of a directed edge (caller -> callee) in the call graph."""
    edge_id: str = Field(
        default_factory=lambda: f"edge-{uuid.uuid4().hex[:12]}",
        description="Unique edge identifier",
    )
    caller_symbol_id: str = Field(..., description="Source node symbol ID (caller)")
    callee_symbol_id: str = Field(..., description="Target node symbol ID (callee)")
    caller_fqn: Optional[str] = Field(default=None, description="FQN of caller symbol")
    callee_fqn: Optional[str] = Field(default=None, description="FQN of callee symbol")
    call_type: str = Field(default="function", description="Call pattern classification kind")
    file_path: str = Field(default="", description="Source file path where call site occurs")
    line: int = Field(default=1, ge=1, description="1-indexed line number of call site")
    column: int = Field(default=0, ge=0, description="0-indexed column offset of call site")
    weight: int = Field(default=1, ge=1, description="Call invocation weight / frequency count")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for edge properties")


class CallGraph(BaseModel):
    """Container holding the complete directed call graph structure and adjacency maps."""
    nodes: Dict[str, CallGraphNode] = Field(
        default_factory=dict,
        description="Map of symbol_id -> CallGraphNode",
    )
    edges: Dict[str, CallGraphEdge] = Field(
        default_factory=dict,
        description="Map of edge_id -> CallGraphEdge",
    )
    adjacency_list: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Forward adjacency map: caller_symbol_id -> [callee_symbol_ids]",
    )
    reverse_adjacency_list: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Reverse adjacency map: callee_symbol_id -> [caller_symbol_ids]",
    )
    node_count: int = Field(default=0, ge=0, description="Total node count in graph")
    edge_count: int = Field(default=0, ge=0, description="Total edge count in graph")


class CallGraphMetrics(BaseModel):
    """Performance telemetry and structural statistics for call graph construction."""
    total_nodes: int = Field(default=0, ge=0, description="Total nodes in call graph")
    total_edges: int = Field(default=0, ge=0, description="Total directed edges in call graph")
    duplicate_nodes: int = Field(default=0, ge=0, description="Count of duplicate node merge attempts")
    duplicate_edges: int = Field(default=0, ge=0, description="Count of duplicate edge merge attempts (weight increments)")
    dangling_edges: int = Field(default=0, ge=0, description="Count of edges referencing missing nodes")
    skipped_edges: int = Field(default=0, ge=0, description="Count of unresolved/invalid calls skipped during edge creation")
    external_nodes: int = Field(default=0, ge=0, description="Count of external / stdlib nodes in graph")
    internal_nodes: int = Field(default=0, ge=0, description="Count of internal repository nodes in graph")
    build_time_ms: float = Field(default=0.0, ge=0.0, description="Graph construction time in milliseconds")
    peak_memory_mb: float = Field(default=0.0, ge=0.0, description="Peak memory usage in megabytes")
    nodes_per_second: float = Field(default=0.0, ge=0.0, description="Node construction throughput per second")
    edges_per_second: float = Field(default=0.0, ge=0.0, description="Edge construction throughput per second")


class CallGraphValidationIssue(BaseModel):
    """Individual issue recorded during call graph integrity validation."""
    severity: str = Field(..., description="'error' or 'warning'")
    code: str = Field(..., description="Issue code, e.g. 'DANGLING_EDGE', 'NODE_COUNT_MISMATCH'")
    message: str = Field(..., description="Human-readable issue explanation")
    node_id: Optional[str] = Field(default=None, description="Associated node symbol_id if applicable")
    edge_id: Optional[str] = Field(default=None, description="Associated edge_id if applicable")


class CallGraphValidationReport(BaseModel):
    """Structured validation report for call graph construction."""
    is_valid: bool = Field(default=True, description="True if no errors were found")
    issues: List[CallGraphValidationIssue] = Field(default_factory=list, description="Validation issues list")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")


class CallGraphResult(BaseModel):
    """Output container for call graph builder execution."""
    result_id: str = Field(
        default_factory=lambda: f"cgres-{uuid.uuid4().hex[:12]}",
        description="Unique call graph result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    graph: CallGraph = Field(default_factory=CallGraph, description="Complete directed call graph container")
    metrics: CallGraphMetrics = Field(default_factory=CallGraphMetrics, description="Graph metrics and performance telemetry")
    validation_report: CallGraphValidationReport = Field(
        default_factory=CallGraphValidationReport,
        description="Graph validation report",
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warning messages recorded during graph building")
    errors: List[str] = Field(default_factory=list, description="Non-fatal error records during graph building")
