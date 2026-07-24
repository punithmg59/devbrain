"""
analysis/call_graph/metrics.py
-------------------------------
Phase 4.8.1 & 4.8.2 — Call Graph Telemetry Metrics Helpers.

Calculates performance telemetry, throughput, memory footprint, and index statistics
for call graph construction and index building.
"""

from __future__ import annotations

import os
import time
from typing import Optional, TYPE_CHECKING

from models.graph_models import CallGraph, CallGraphMetrics
from models.graph_index_models import GraphIndex, GraphIndexMetrics

if TYPE_CHECKING:
    from analysis.call_graph.query_engine import CallGraphQueryEngine


def compute_metrics(
    graph: CallGraph,
    build_time_ms: float = 0.0,
    duplicate_nodes: int = 0,
    duplicate_edges: int = 0,
    dangling_edges: int = 0,
    skipped_edges: int = 0,
) -> CallGraphMetrics:
    """
    Compute CallGraphMetrics telemetry from a completed CallGraph.
    """
    total_nodes = len(graph.nodes)
    total_edges = len(graph.edges)

    external_nodes = sum(1 for n in graph.nodes.values() if n.is_external)
    internal_nodes = total_nodes - external_nodes

    build_sec = max(0.0001, build_time_ms / 1000.0)
    nodes_per_second = total_nodes / build_sec
    edges_per_second = total_edges / build_sec

    return CallGraphMetrics(
        total_nodes=total_nodes,
        total_edges=total_edges,
        duplicate_nodes=duplicate_nodes,
        duplicate_edges=duplicate_edges,
        dangling_edges=dangling_edges,
        skipped_edges=skipped_edges,
        external_nodes=external_nodes,
        internal_nodes=internal_nodes,
        build_time_ms=round(build_time_ms, 3),
        peak_memory_mb=round(_get_memory_mb(), 2),
        nodes_per_second=round(nodes_per_second, 1),
        edges_per_second=round(edges_per_second, 1),
    )


def compute_index_metrics(
    graph_index: GraphIndex,
    build_time_ms: float = 0.0,
    duplicate_index_entries: int = 0,
    query_engine: Optional[CallGraphQueryEngine] = None,
) -> GraphIndexMetrics:
    """
    Compute GraphIndexMetrics telemetry from a completed GraphIndex.
    """
    indexed_nodes = len(graph_index.node_by_symbol_id)
    indexed_edges = sum(len(edges) for edges in graph_index.edges_by_caller.values())

    lookups_per_second = 0.0
    if query_engine and indexed_nodes > 0:
        lookups_per_second = _benchmark_lookups(query_engine)

    return GraphIndexMetrics(
        indexed_nodes=indexed_nodes,
        indexed_edges=indexed_edges,
        caller_index_size=len(graph_index.edges_by_caller),
        callee_index_size=len(graph_index.edges_by_callee),
        file_index_size=len(graph_index.nodes_by_file),
        fqn_index_size=len(graph_index.node_by_fqn),
        duplicate_index_entries=duplicate_index_entries,
        build_time_ms=round(build_time_ms, 3),
        peak_memory_mb=round(_get_memory_mb(), 2),
        lookups_per_second=round(lookups_per_second, 1),
    )


def _benchmark_lookups(query_engine: CallGraphQueryEngine, sample_count: int = 1000) -> float:
    """Measure O(1) query throughput lookups per second."""
    try:
        sample_ids = list(query_engine.index.node_by_symbol_id.keys())[:sample_count]
        if not sample_ids:
            return 0.0

        t0 = time.perf_counter()
        for sym_id in sample_ids:
            _ = query_engine.find_node(sym_id)
            _ = query_engine.find_callers(sym_id)
            _ = query_engine.find_callees(sym_id)
        dt = max(0.000001, time.perf_counter() - t0)

        total_queries = len(sample_ids) * 3
        return total_queries / dt
    except Exception:
        return 0.0


def _get_memory_mb() -> float:
    """Return current process RSS memory footprint in megabytes."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return 0.0
