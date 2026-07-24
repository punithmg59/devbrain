"""
analysis/call_graph/metrics.py
-------------------------------
Phase 4.8.1, 4.8.2, 4.8.3 — Call Graph Telemetry Metrics Helpers.

Calculates performance telemetry, throughput, memory footprint, index statistics,
and validation metrics.
"""

from __future__ import annotations

import os
import time
from typing import Optional, TYPE_CHECKING

from models.graph_models import CallGraph, CallGraphMetrics
from models.graph_index_models import GraphIndex, GraphIndexMetrics
from models.graph_validation_models import ValidationMetrics

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
    total_nodes = len(graph.nodes) if graph and graph.nodes else 0
    total_edges = len(graph.edges) if graph and graph.edges else 0

    external_nodes = sum(1 for n in graph.nodes.values() if n.is_external) if graph and graph.nodes else 0
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
    indexed_nodes = len(graph_index.node_by_symbol_id) if graph_index and graph_index.node_by_symbol_id else 0
    indexed_edges = sum(len(edges) for edges in graph_index.edges_by_caller.values()) if graph_index and graph_index.edges_by_caller else 0

    lookups_per_second = 0.0
    if query_engine and indexed_nodes > 0:
        lookups_per_second = _benchmark_lookups(query_engine)

    return GraphIndexMetrics(
        indexed_nodes=indexed_nodes,
        indexed_edges=indexed_edges,
        caller_index_size=len(graph_index.edges_by_caller) if graph_index and graph_index.edges_by_caller else 0,
        callee_index_size=len(graph_index.edges_by_callee) if graph_index and graph_index.edges_by_callee else 0,
        file_index_size=len(graph_index.nodes_by_file) if graph_index and graph_index.nodes_by_file else 0,
        fqn_index_size=len(graph_index.node_by_fqn) if graph_index and graph_index.node_by_fqn else 0,
        duplicate_index_entries=duplicate_index_entries,
        build_time_ms=round(build_time_ms, 3),
        peak_memory_mb=round(_get_memory_mb(), 2),
        lookups_per_second=round(lookups_per_second, 1),
    )


def compute_validation_metrics(
    graph: Optional[CallGraph] = None,
    graph_index: Optional[GraphIndex] = None,
    rules_executed: int = 0,
    info_count: int = 0,
    warning_count: int = 0,
    error_count: int = 0,
    critical_count: int = 0,
    validation_duration_ms: float = 0.0,
) -> ValidationMetrics:
    """
    Compute ValidationMetrics telemetry from a completed graph validation pass.
    """
    validated_nodes = len(graph.nodes) if graph and graph.nodes else 0
    validated_edges = len(graph.edges) if graph and graph.edges else 0

    validated_indexes = 0
    if graph_index:
        validated_indexes = (
            len(graph_index.node_by_symbol_id or {})
            + len(graph_index.node_by_fqn or {})
            + len(graph_index.nodes_by_file or {})
            + len(graph_index.edges_by_caller or {})
        )

    return ValidationMetrics(
        validated_nodes=validated_nodes,
        validated_edges=validated_edges,
        validated_indexes=validated_indexes,
        rules_executed=rules_executed,
        info_count=info_count,
        warning_count=warning_count,
        error_count=error_count,
        critical_count=critical_count,
        validation_duration_ms=round(validation_duration_ms, 3),
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
