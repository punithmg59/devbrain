# backend/graph_query_engine/tests/unit/optimizer/test_diagnostics.py
"""Unit tests for thread-safe diagnostics collector."""

from graph_query_engine.optimizer import OptimizationDiagnostics


def test_diagnostics_recording():
    diag = OptimizationDiagnostics()

    diag.record_applied("filter_pushdown", "Pushed filter down past join")
    diag.record_skipped("join_reordering", "No cost stats available")
    diag.record_rejected("custom_rule", "Division by zero")

    assert len(diag.applied) == 1
    assert len(diag.skipped) == 1
    assert len(diag.rejected) == 1

    summary = diag.summary()
    assert summary["applied"] == 1
    assert summary["skipped"] == 1
    assert summary["rejected"] == 1
