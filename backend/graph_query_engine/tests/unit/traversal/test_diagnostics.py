# backend/graph_query_engine/tests/unit/traversal/test_diagnostics.py
"""Unit tests for TraversalDiagnostics."""

from graph_query_engine.traversal import TraversalDiagnostics


def test_diagnostics_collection():
    diag = TraversalDiagnostics()

    diag.record_info("Algorithm", "Starting test")
    diag.record_warning("Limit", "Max depth reached")
    diag.record_error("Graph", "Missing node key")
    diag.record_pruning("max_depth_reached")
    diag.record_cache_hit()
    diag.record_cache_miss()

    assert len(diag.records) == 3
    assert len(diag.warnings) == 1
    assert len(diag.errors) == 1

    summary = diag.summary()
    assert summary["warnings_count"] == 1
    assert summary["cache_stats"]["hits"] == 1
    assert summary["cache_stats"]["misses"] == 1
