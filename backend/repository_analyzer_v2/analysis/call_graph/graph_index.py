"""
analysis/call_graph/graph_index.py
-----------------------------------
Phase 4.8.2 — Call Graph Multi-Index Builder Engine.

Transforms a `CallGraph` (Phase 4.8.1) into an optimized `GraphIndex` containing
fast O(1) lookup tables for nodes by symbol ID, FQN, file path, caller outgoing edges,
callee incoming edges, and file edges.

Design Principles
-----------------
- **Streaming O(V + E) Construction**: Single-pass indexing walk over graph nodes and edges.
- **Zero Object Duplication**: Reuses references to existing `CallGraphNode` and `CallGraphEdge`
  Pydantic objects without copying data contracts.
- **Cross-Platform Path Normalization**: Normalizes Windows slashes to POSIX format.
- **Fault-Tolerant Execution**: Malformed node/edge entities log structured warnings and continue.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Set

from models.graph_models import (
    CallGraph,
    CallGraphEdge,
    CallGraphNode,
    CallGraphResult,
)
from models.graph_index_models import (
    CallGraphIndexResult,
    GraphIndex,
    GraphIndexMetrics,
)
from analysis.call_graph.index_validator import GraphIndexValidator
from analysis.call_graph.metrics import compute_index_metrics
from utils.logger import get_logger

logger = get_logger(__name__)


class CallGraphIndexBuilder:
    """
    Index builder engine that constructs fast O(1) lookup tables from a CallGraph.

    Usage::

        builder = CallGraphIndexBuilder(repository_id="repo1")
        index_result = builder.build_index(call_graph_result)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._validator = GraphIndexValidator()

    def build_index(
        self,
        graph_result: CallGraphResult,
    ) -> CallGraphIndexResult:
        """
        Build a `GraphIndex` and return `CallGraphIndexResult` containing the index and query engine.

        Parameters
        ----------
        graph_result:
            Output from Phase 4.8.1 `CallGraphBuilder`.

        Returns
        -------
        CallGraphIndexResult
        """
        start_time = time.perf_counter()
        graph = graph_result.graph

        logger.info(
            f"[CallGraphIndexBuilder] Building graph index for repo '{self.repository_id}' "
            f"(Nodes={graph.node_count:,}, Edges={graph.edge_count:,})"
        )

        node_by_symbol_id: Dict[str, CallGraphNode] = {}
        node_by_fqn: Dict[str, CallGraphNode] = {}
        nodes_by_file: Dict[str, List[CallGraphNode]] = {}

        edges_by_caller: Dict[str, List[CallGraphEdge]] = {}
        edges_by_callee: Dict[str, List[CallGraphEdge]] = {}
        edges_by_file: Dict[str, List[CallGraphEdge]] = {}

        callers_index: Dict[str, Set[str]] = {}
        callees_index: Dict[str, Set[str]] = {}

        warnings: List[str] = []
        errors: List[str] = []
        duplicate_index_entries = 0

        # 1. Index Nodes (SymbolId, FQN, File)
        for sym_id, node in graph.nodes.items():
            try:
                # SymbolId index
                node_by_symbol_id[sym_id] = node

                # FQN index
                if node.fully_qualified_name:
                    if node.fully_qualified_name in node_by_fqn:
                        duplicate_index_entries += 1
                    node_by_fqn[node.fully_qualified_name] = node

                # File index
                if node.file_path:
                    norm_path = self._norm_path(node.file_path)
                    nodes_by_file.setdefault(norm_path, []).append(node)

            except Exception as exc:
                msg = f"Failed to index CallGraphNode '{sym_id}': {exc}"
                logger.warning(f"[CallGraphIndexBuilder] {msg}")
                errors.append(msg)

        # 2. Index Edges (Caller, Callee, File, Callers/Callees lookups)
        for edge_id, edge in graph.edges.items():
            try:
                caller_id = edge.caller_symbol_id
                callee_id = edge.callee_symbol_id

                # Outgoing edges by caller
                edges_by_caller.setdefault(caller_id, []).append(edge)

                # Incoming edges by callee
                edges_by_callee.setdefault(callee_id, []).append(edge)

                # File edge index
                if edge.file_path:
                    norm_path = self._norm_path(edge.file_path)
                    edges_by_file.setdefault(norm_path, []).append(edge)

                # Callers / Callees symbol ID lookups
                callers_index.setdefault(callee_id, set()).add(caller_id)
                callees_index.setdefault(caller_id, set()).add(callee_id)

            except Exception as exc:
                msg = f"Failed to index CallGraphEdge '{edge_id}': {exc}"
                logger.warning(f"[CallGraphIndexBuilder] {msg}")
                errors.append(msg)

        # Convert Callers/Callees sets to sorted lists for serialization
        final_callers_index: Dict[str, List[str]] = {k: sorted(list(v)) for k, v in callers_index.items()}
        final_callees_index: Dict[str, List[str]] = {k: sorted(list(v)) for k, v in callees_index.items()}

        graph_index = GraphIndex(
            node_by_symbol_id=node_by_symbol_id,
            node_by_fqn=node_by_fqn,
            nodes_by_file=nodes_by_file,
            edges_by_caller=edges_by_caller,
            edges_by_callee=edges_by_callee,
            edges_by_file=edges_by_file,
            callers_index=final_callers_index,
            callees_index=final_callees_index,
        )

        # 3. Instantiate QueryEngine with constructed index
        from analysis.call_graph.query_engine import CallGraphQueryEngine
        query_engine = CallGraphQueryEngine(graph=graph, graph_index=graph_index)

        # 4. Validate Index Integrity
        val_report = self._validator.validate(graph_index, graph)
        warnings.extend([i.message for i in val_report.issues if i.severity == "warning"])
        errors.extend([i.message for i in val_report.issues if i.severity == "error"])

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = compute_index_metrics(
            graph_index=graph_index,
            build_time_ms=duration_ms,
            duplicate_index_entries=duplicate_index_entries,
            query_engine=query_engine,
        )

        logger.info(
            f"[CallGraphIndexBuilder] Built graph index: IndexedNodes={metrics.indexed_nodes:,}, "
            f"IndexedEdges={metrics.indexed_edges:,}, FQNIndex={metrics.fqn_index_size:,}, "
            f"BuildTime={duration_ms:.2f}ms, Lookups/sec={metrics.lookups_per_second:,.0f}"
        )

        return CallGraphIndexResult(
            repository_id=self.repository_id,
            graph=graph,
            graph_index=graph_index,
            query_engine=query_engine,
            metrics=metrics,
            validation_report=val_report,
            warnings=warnings,
            errors=errors,
        )

    @staticmethod
    def _norm_path(path: str) -> str:
        """Normalize file path to POSIX format."""
        return path.replace("\\", "/").strip("/")
