# backend/graph_query_engine/tests/unit/traversal/test_validation.py
"""Unit tests for TraversalValidator."""

import pytest
from graph_query_engine.traversal import (
    TraversalValidator,
    TraversalResult,
)


def test_validator_prerequisites_clean():
    report = TraversalValidator.validate_prerequisites(
        graph_view={"A": ["B"]},
        start_nodes=["A"],
        max_depth=5,
    )
    assert report.valid is True


def test_validator_prerequisites_missing_graph():
    report = TraversalValidator.validate_prerequisites(
        graph_view=None,
        start_nodes=["A"],
    )
    assert report.valid is False


def test_validator_prerequisites_empty_roots():
    report = TraversalValidator.validate_prerequisites(
        graph_view={"A": []},
        start_nodes=[],
    )
    assert report.valid is False


def test_validator_result_clean():
    res = TraversalResult(visited_nodes=["A"], execution_time_ms=10.5)
    report = TraversalValidator.validate_result(res)
    assert report.valid is True
