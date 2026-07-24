"""
analysis/call_graph/query_engine.py
------------------------------------
Phase 4.8.2 — Call Graph Query Engine Gateway.

Provides a fast, zero-traversal O(1) public API for querying nodes, edges, FQNs,
files, callers, callees, incoming edges, and outgoing edges using `GraphIndex`.

Design Principles
-----------------
- **Zero Graph Traversal**: Queries rely strictly on pre-computed O(1) index tables;
  does NOT perform DFS/BFS, reachability, path search, or cycle detection.
- **Single Stable API Gateway**: Every higher-level DevBrain component (Dependency Graph,
  Knowledge Graph, Engineering Evidence, Change Intelligence) accesses the graph exclusively
  through `CallGraphQueryEngine`.
- **Path Neutrality**: Normalizes Windows slashes to POSIX format for robust file queries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.graph_models import CallGraph, CallGraphEdge, CallGraphNode
from models.graph_index_models import GraphIndex
from utils.logger import get_logger

logger = get_logger(__name__)


class CallGraphQueryEngine:
    """
    Public query engine gateway providing O(1) indexed lookups over a CallGraph.

    Usage::

        engine = CallGraphQueryEngine(graph=call_graph, graph_index=graph_index)
        node = engine.find_node_by_fqn("fastapi.applications.FastAPI")
        callers = engine.find_callers(node.symbol_id)
        outgoing = engine.find_outgoing_edges(node.symbol_id)
    """

    def __init__(
        self,
        graph: CallGraph,
        graph_index: GraphIndex,
    ) -> None:
        self.graph = graph
        self.index = graph_index

    def find_node(self, symbol_id: str) -> Optional[CallGraphNode]:
        """O(1) lookup of a CallGraphNode by symbol_id."""
        if not symbol_id:
            return None
        return self.index.node_by_symbol_id.get(symbol_id)

    def find_node_by_fqn(self, fqn: str) -> Optional[CallGraphNode]:
        """O(1) lookup of a CallGraphNode by fully qualified name."""
        if not fqn:
            return None
        return self.index.node_by_fqn.get(fqn)

    def find_nodes_by_file(self, path: str) -> List[CallGraphNode]:
        """O(1) lookup of all CallGraphNode instances defined in a source file."""
        if not path:
            return []
        norm_path = self._norm_path(path)
        return self.index.nodes_by_file.get(norm_path, [])

    def find_callers(self, symbol_id: str) -> List[str]:
        """
        O(1) lookup of all caller SymbolIds targeting the specified callee symbol_id.

        Returns list of caller symbol_id strings.
        """
        if not symbol_id:
            return []
        return self.index.callers_index.get(symbol_id, [])

    def find_callees(self, symbol_id: str) -> List[str]:
        """
        O(1) lookup of all callee SymbolIds invoked by the specified caller symbol_id.

        Returns list of callee symbol_id strings.
        """
        if not symbol_id:
            return []
        return self.index.callees_index.get(symbol_id, [])

    def find_outgoing_edges(self, symbol_id: str) -> List[CallGraphEdge]:
        """O(1) lookup of all outgoing CallGraphEdge instances originating from caller symbol_id."""
        if not symbol_id:
            return []
        return self.index.edges_by_caller.get(symbol_id, [])

    def find_incoming_edges(self, symbol_id: str) -> List[CallGraphEdge]:
        """O(1) lookup of all incoming CallGraphEdge instances targeting callee symbol_id."""
        if not symbol_id:
            return []
        return self.index.edges_by_callee.get(symbol_id, [])

    def find_edges_in_file(self, path: str) -> List[CallGraphEdge]:
        """O(1) lookup of all CallGraphEdge instances occurring within a source file."""
        if not path:
            return []
        norm_path = self._norm_path(path)
        return self.index.edges_by_file.get(norm_path, [])

    def contains_node(self, symbol_id: str) -> bool:
        """Return True if symbol_id exists in graph nodes."""
        if not symbol_id:
            return False
        return symbol_id in self.index.node_by_symbol_id

    def contains_edge(self, caller_symbol_id: str, callee_symbol_id: str) -> bool:
        """Return True if a directed edge exists between caller_symbol_id and callee_symbol_id."""
        if not caller_symbol_id or not callee_symbol_id:
            return False
        callees = self.index.callees_index.get(caller_symbol_id, [])
        return callee_symbol_id in callees

    def graph_statistics(self) -> Dict[str, Any]:
        """Return statistical summary of graph and index sizes."""
        return {
            "node_count": self.graph.node_count,
            "edge_count": self.graph.edge_count,
            "fqn_indexed_nodes": len(self.index.node_by_fqn),
            "files_indexed": len(self.index.nodes_by_file),
            "callers_indexed": len(self.index.callers_index),
            "callees_indexed": len(self.index.callees_index),
        }

    @staticmethod
    def _norm_path(path: str) -> str:
        """Normalize file path to POSIX format."""
        return path.replace("\\", "/").strip("/")
