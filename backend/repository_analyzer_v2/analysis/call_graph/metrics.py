"""
analysis/call_graph/metrics.py
-------------------------------
Phase 4.8.1 — Call Graph Metrics Telemetry Helpers.

Calculates performance telemetry, throughput, memory footprint, and graph statistics
for call graph construction.
"""

from __future__ import annotations

import os
from typing import Optional

from models.graph_models import CallGraph, CallGraphMetrics


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

    Parameters
    ----------
    graph:
        Constructed `CallGraph` instance.
    build_time_ms:
        Construction time in milliseconds.
    duplicate_nodes:
        Count of duplicate node additions attempted.
    duplicate_edges:
        Count of duplicate edge merge attempts.
    dangling_edges:
        Count of dangling edge references.
    skipped_edges:
        Count of skipped unresolved call records.

    Returns
    -------
    CallGraphMetrics
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


def _get_memory_mb() -> float:
    """Return current process RSS memory footprint in megabytes."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return 0.0
