"""
analysis/call_graph/graph_builder.py
-------------------------------------
Phase 4.8.1 — Call Graph Builder Engine.

Transforms `FunctionCallDetectionResult` (Phase 4.7.2) and `SymbolTable` (Phase 4.4)
into a directed call graph (`CallGraphResult`) containing nodes, directed edges,
forward/reverse adjacency lists, structural metrics, and validation reports.

Design Principles
-----------------
- **Streaming O(V + E) Construction**: Single-pass node and edge processing with zero quadratic scans.
- **Zero-Duplicate Invariant**: Nodes keyed uniquely by `symbol_id`; identical directed edges
  merged via `weight` property increments.
- **Fault-Tolerant Execution**: Invalid or malformed call records log structured warnings
  and increment `skipped_edges` without interrupting graph construction.
- **Microsecond Adjacency Lookups**: Pre-populated forward and reverse adjacency list lookups.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Set, Tuple

from models.call_models import FunctionCallDetectionResult
from models.graph_models import (
    CallGraph,
    CallGraphEdge,
    CallGraphNode,
    CallGraphResult,
)
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.call_graph.validator import CallGraphValidator
from analysis.call_graph.metrics import compute_metrics
from utils.logger import get_logger

logger = get_logger(__name__)


class CallGraphBuilder:
    """
    Builder engine that constructs directed call graphs from function call detection results.

    Usage::

        builder = CallGraphBuilder(repository_id="repo1")
        result = builder.build_graph(call_detection_result, symbol_table)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._validator = CallGraphValidator()

    def build_graph(
        self,
        call_detection_result: FunctionCallDetectionResult,
        symbol_table: Optional[SymbolTable] = None,
    ) -> CallGraphResult:
        """
        Build a directed call graph from `FunctionCallDetectionResult` and `SymbolTable`.

        Parameters
        ----------
        call_detection_result:
            Output from Phase 4.7.2 `FunctionCallDetector`.
        symbol_table:
            Optional repository `SymbolTable` used to pre-populate node details.

        Returns
        -------
        CallGraphResult
        """
        start_time = time.perf_counter()
        logger.info(
            f"[CallGraphBuilder] Starting call graph construction for repo '{self.repository_id}' "
            f"({len(call_detection_result.calls)} calls to process)"
        )

        nodes: Dict[str, CallGraphNode] = {}
        edges: Dict[str, CallGraphEdge] = {}
        edge_key_map: Dict[Tuple[str, str], str] = {}  # (caller_id, callee_id) -> edge_id

        adj_list: Dict[str, Set[str]] = {}
        rev_adj_list: Dict[str, Set[str]] = {}

        warnings: List[str] = []
        errors: List[str] = []

        duplicate_nodes = 0
        duplicate_edges = 0
        dangling_edges = 0
        skipped_edges = 0

        # 1. Pre-populate Nodes from SymbolTable (Functions, Methods, Classes, Constructors)
        if symbol_table:
            for sym in symbol_table.symbols.values():
                kind_val = sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind)
                if kind_val in ("function", "method", "class"):
                    node = self._create_node_from_symbol(sym)
                    if node.symbol_id in nodes:
                        duplicate_nodes += 1
                    else:
                        nodes[node.symbol_id] = node

        # 2. Streaming Edge & Node Construction from CallRecord Entries
        for call_id, call in call_detection_result.calls.items():
            try:
                caller_id = call.caller_symbol_id
                callee_id = call.callee_symbol_id

                # Handle External / Synthesized Callee Nodes
                if not callee_id and (call.is_external or call.callee_name):
                    raw_name = call.callee_name or "unknown"
                    callee_id = f"external:{raw_name}"
                    if callee_id not in nodes:
                        ext_node = CallGraphNode(
                            symbol_id=callee_id,
                            fully_qualified_name=f"external.{raw_name}",
                            name=raw_name,
                            node_type="external",
                            file_path=call.file_path,
                            line=call.line,
                            column=call.column,
                            is_external=True,
                        )
                        nodes[callee_id] = ext_node

                # Validation checks on endpoints
                if not caller_id or not callee_id:
                    skipped_edges += 1
                    continue

                # Ensure caller node exists in nodes map
                if caller_id not in nodes:
                    if symbol_table and caller_id in symbol_table:
                        sym = symbol_table.get_symbol(caller_id)
                        if sym:
                            nodes[caller_id] = self._create_node_from_symbol(sym)
                    else:
                        # Synthesize fallback caller node
                        nodes[caller_id] = CallGraphNode(
                            symbol_id=caller_id,
                            fully_qualified_name=call.caller_fqn or caller_id,
                            name=(call.caller_fqn or caller_id).split(".")[-1],
                            node_type="function",
                            file_path=call.file_path,
                            line=call.line,
                            column=call.column,
                        )

                # Ensure callee node exists in nodes map
                if callee_id not in nodes:
                    if symbol_table and callee_id in symbol_table:
                        sym = symbol_table.get_symbol(callee_id)
                        if sym:
                            nodes[callee_id] = self._create_node_from_symbol(sym)
                    else:
                        # Synthesize fallback callee node
                        nodes[callee_id] = CallGraphNode(
                            symbol_id=callee_id,
                            fully_qualified_name=call.callee_fqn or call.callee_name or callee_id,
                            name=call.callee_name or callee_id,
                            node_type="function" if not call.is_constructor else "constructor",
                            file_path=call.file_path,
                            line=call.line,
                            column=call.column,
                            is_external=call.is_external,
                        )

                # Deduplicate Edges via (caller_id, callee_id) key map
                edge_key = (caller_id, callee_id)
                if edge_key in edge_key_map:
                    existing_edge_id = edge_key_map[edge_key]
                    edges[existing_edge_id].weight += 1
                    duplicate_edges += 1
                else:
                    call_type_str = call.call_type.value if hasattr(call.call_type, "value") else str(call.call_type)
                    edge = CallGraphEdge(
                        caller_symbol_id=caller_id,
                        callee_symbol_id=callee_id,
                        caller_fqn=call.caller_fqn or nodes[caller_id].fully_qualified_name,
                        callee_fqn=call.callee_fqn or nodes[callee_id].fully_qualified_name,
                        call_type=call_type_str,
                        file_path=call.file_path,
                        line=call.line,
                        column=call.column,
                        weight=1,
                    )
                    edges[edge.edge_id] = edge
                    edge_key_map[edge_key] = edge.edge_id

                # Update Adjacency Lists
                adj_list.setdefault(caller_id, set()).add(callee_id)
                rev_adj_list.setdefault(callee_id, set()).add(caller_id)

            except Exception as exc:
                msg = f"Failed to process CallRecord '{call_id}' in '{call.file_path}': {exc}"
                logger.warning(f"[CallGraphBuilder] {msg}")
                errors.append(msg)
                skipped_edges += 1

        # Convert Adjacency Sets to Lists for Pydantic V2 serialization
        final_adj_list: Dict[str, List[str]] = {k: sorted(list(v)) for k, v in adj_list.items()}
        final_rev_adj_list: Dict[str, List[str]] = {k: sorted(list(v)) for k, v in rev_adj_list.items()}

        graph = CallGraph(
            nodes=nodes,
            edges=edges,
            adjacency_list=final_adj_list,
            reverse_adjacency_list=final_rev_adj_list,
            node_count=len(nodes),
            edge_count=len(edges),
        )

        # 3. Validate Graph Integrity
        val_report = self._validator.validate(graph)
        warnings.extend([i.message for i in val_report.issues if i.severity == "warning"])
        errors.extend([i.message for i in val_report.issues if i.severity == "error"])

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = compute_metrics(
            graph=graph,
            build_time_ms=duration_ms,
            duplicate_nodes=duplicate_nodes,
            duplicate_edges=duplicate_edges,
            dangling_edges=dangling_edges,
            skipped_edges=skipped_edges,
        )

        logger.info(
            f"[CallGraphBuilder] Built call graph: Nodes={graph.node_count:,}, Edges={graph.edge_count:,}, "
            f"BuildTime={duration_ms:.2f}ms, Memory={metrics.peak_memory_mb:.2f}MB"
        )

        return CallGraphResult(
            repository_id=self.repository_id,
            graph=graph,
            metrics=metrics,
            validation_report=val_report,
            warnings=warnings,
            errors=errors,
        )

    @staticmethod
    def _create_node_from_symbol(sym: Symbol) -> CallGraphNode:
        """Construct a CallGraphNode from a SymbolTable Symbol."""
        line = sym.location.range.start.line if sym.location and sym.location.range else 1
        col = sym.location.range.start.column if sym.location and sym.location.range else 0
        node_type = sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind)
        return CallGraphNode(
            symbol_id=sym.id,
            fully_qualified_name=sym.fqn,
            name=sym.name,
            node_type=node_type,
            file_path=sym.file_path or "",
            line=line,
            column=col,
            is_external=False,
            metadata=sym.metadata or {},
        )
