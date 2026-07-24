"""
analysis/call_graph/__init__.py
-------------------------------
Phase 4.8.1 & Phase 4.8.2 — Call Graph & Query Engine Package.

Exports directed call graph models, builder, indexer, query engine, validation,
and telemetry helpers for Phase 4.8.1 and Phase 4.8.2.
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
from models.graph_index_models import (
    CallGraphIndexResult,
    GraphIndex,
    GraphIndexMetrics,
    GraphIndexValidationIssue,
    GraphIndexValidationReport,
)
from analysis.call_graph.exceptions import (
    CallGraphBuildError,
    DuplicateEdgeWarning,
    DuplicateIndexWarning,
    DuplicateNodeError,
    GraphIndexError,
    InvalidEdgeError,
    InvalidIndexError,
    InvalidNodeError,
    MissingEdgeError,
    MissingNodeError,
)
from analysis.call_graph.graph_builder import CallGraphBuilder
from analysis.call_graph.graph_index import CallGraphIndexBuilder
from analysis.call_graph.query_engine import CallGraphQueryEngine
from analysis.call_graph.validator import CallGraphValidator
from analysis.call_graph.index_validator import GraphIndexValidator
from analysis.call_graph.metrics import compute_index_metrics, compute_metrics

__all__ = [
    # Graph Construction (Phase 4.8.1)
    "CallGraphBuilder",
    "CallGraphValidator",
    "CallGraphNode",
    "CallGraphEdge",
    "CallGraph",
    "CallGraphMetrics",
    "CallGraphValidationIssue",
    "CallGraphValidationReport",
    "CallGraphResult",
    # Graph Index & Query Engine (Phase 4.8.2)
    "CallGraphIndexBuilder",
    "CallGraphQueryEngine",
    "GraphIndexValidator",
    "GraphIndex",
    "GraphIndexMetrics",
    "GraphIndexValidationIssue",
    "GraphIndexValidationReport",
    "CallGraphIndexResult",
    # Exceptions
    "CallGraphBuildError",
    "InvalidNodeError",
    "InvalidEdgeError",
    "DuplicateNodeError",
    "DuplicateEdgeWarning",
    "GraphIndexError",
    "InvalidIndexError",
    "MissingNodeError",
    "MissingEdgeError",
    "DuplicateIndexWarning",
    # Metrics
    "compute_metrics",
    "compute_index_metrics",
]
