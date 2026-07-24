"""
analysis/call_graph/__init__.py
-------------------------------
Phase 4.8.1 — Call Graph Models & Graph Builder Package.

Exports directed graph models, call graph builder, validator, telemetry metrics,
and custom exceptions for Phase 4.8.1.
"""

from models.graph_models import (
    CallGraph,
    CallGraphEdge,
    CallGraphMetrics,
    CallGraphNode,
    CallGraphResult,
    CallGraphValidationIssue,
    CallGraphValidationReport,
)
from analysis.call_graph.exceptions import (
    CallGraphBuildError,
    DuplicateEdgeWarning,
    DuplicateNodeError,
    InvalidEdgeError,
    InvalidNodeError,
)
from analysis.call_graph.graph_builder import CallGraphBuilder
from analysis.call_graph.validator import CallGraphValidator
from analysis.call_graph.metrics import compute_metrics

__all__ = [
    "CallGraphBuilder",
    "CallGraphValidator",
    "CallGraphNode",
    "CallGraphEdge",
    "CallGraph",
    "CallGraphMetrics",
    "CallGraphValidationIssue",
    "CallGraphValidationReport",
    "CallGraphResult",
    "CallGraphBuildError",
    "InvalidNodeError",
    "InvalidEdgeError",
    "DuplicateNodeError",
    "DuplicateEdgeWarning",
    "compute_metrics",
]
