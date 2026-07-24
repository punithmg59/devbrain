"""
analysis/call_graph/__init__.py
-------------------------------
Phase 4.8.1, 4.8.2, 4.8.3 — Call Graph, Query Engine & Validation Package.

Exports directed call graph models, builder, indexer, query engine, read-only validator,
rules suite, and telemetry helpers.
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
from models.graph_validation_models import (
    GraphValidationResult,
    ValidationIssue,
    ValidationMetrics,
    ValidationReport,
    ValidationSeverity,
)
from analysis.call_graph.exceptions import (
    CallGraphBuildError,
    DuplicateEdgeWarning,
    DuplicateIndexWarning,
    DuplicateNodeError,
    EdgeValidationError,
    GraphConsistencyError,
    GraphIndexError,
    IndexValidationError,
    IntegrityValidationError,
    InvalidEdgeError,
    InvalidIndexError,
    InvalidNodeError,
    MissingEdgeError,
    MissingNodeError,
    NodeValidationError,
    ValidationError,
)
from analysis.call_graph.graph_builder import CallGraphBuilder
from analysis.call_graph.graph_index import CallGraphIndexBuilder
from analysis.call_graph.query_engine import CallGraphQueryEngine
from analysis.call_graph.validator import CallGraphValidator, GraphValidator
from analysis.call_graph.validation_rules import (
    BaseValidationRule,
    EdgeValidationRule,
    GraphConsistencyRule,
    IndexValidationRule,
    NodeValidationRule,
    ReferenceIntegrityRule,
    StructuralIntegrityRule,
)
from analysis.call_graph.metrics import (
    compute_index_metrics,
    compute_metrics,
    compute_validation_metrics,
)

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
    "GraphIndex",
    "GraphIndexMetrics",
    "GraphIndexValidationIssue",
    "GraphIndexValidationReport",
    "CallGraphIndexResult",
    # Graph Validation & Integrity Framework (Phase 4.8.3)
    "GraphValidator",
    "BaseValidationRule",
    "StructuralIntegrityRule",
    "NodeValidationRule",
    "EdgeValidationRule",
    "IndexValidationRule",
    "GraphConsistencyRule",
    "ReferenceIntegrityRule",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationMetrics",
    "ValidationReport",
    "GraphValidationResult",
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
    "ValidationError",
    "NodeValidationError",
    "EdgeValidationError",
    "IntegrityValidationError",
    "IndexValidationError",
    "GraphConsistencyError",
    # Metrics
    "compute_metrics",
    "compute_index_metrics",
    "compute_validation_metrics",
]
