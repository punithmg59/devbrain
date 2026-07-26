"""
Graph View Package - Immutable Graph Access Layer.
"""

from graph_query_engine.contracts.view import IGraphView
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.factory import GraphViewFactory
from graph_query_engine.view.graph_view import GraphView
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.lifecycle import (
    GraphViewLifecycle,
    GraphViewLifecycleState,
    GraphViewLifecycleStatus,
)
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo
from graph_query_engine.view.statistics import GraphStatistics
from graph_query_engine.view.validation import (
    GraphViewValidationReport,
    GraphViewValidationViolation,
    GraphViewValidator,
)

__all__ = [
    "IGraphView",
    "GraphView",
    "GraphIdentity",
    "ImmutableNodeView",
    "ImmutableEdgeView",
    "GraphMetadata",
    "GraphSnapshotInfo",
    "GraphStatistics",
    "GraphViewValidator",
    "GraphViewValidationReport",
    "GraphViewValidationViolation",
    "GraphViewFactory",
    "GraphViewBuilder",
    "GraphViewLifecycle",
    "GraphViewLifecycleState",
    "GraphViewLifecycleStatus",
]
