"""
Graph Query Engine Contracts Package.
"""

from graph_query_engine.contracts.adapter import IGraphAdapter
from graph_query_engine.contracts.api import IQueryEngineAPI
from graph_query_engine.contracts.budget import IQueryBudgetManager
from graph_query_engine.contracts.capabilities import (
    ICapabilityRegistry,
    ICapabilityValidator,
)
from graph_query_engine.contracts.diagnostics import IQueryDiagnostics
from graph_query_engine.contracts.extension import IQueryExtension
from graph_query_engine.contracts.index import (
    IIndex,
    IIndexBuilder,
    IIndexDescriptor,
    IIndexFactory,
    IIndexLifecycle,
    IIndexMetadata,
    IIndexProvider,
    IIndexRegistry,
    IIndexStatistics,
    IIndexValidator,
)
from graph_query_engine.contracts.model import IQueryContext
from graph_query_engine.contracts.pipeline import IQueryExecutor, IQueryPipeline
from graph_query_engine.contracts.planner import (
    IPlannerCapabilities,
    IPlannerContext,
    IPlannerDiagnostics,
    IPlannerLifecycle,
    IPlannerRegistry,
    IPlannerSession,
    IQueryPlanner,
)
from graph_query_engine.contracts.traversal import (
    ITraversalRegistry,
    ITraversalStrategy,
)
from graph_query_engine.contracts.validation import IQueryValidator
from graph_query_engine.contracts.view import IGraphView

__all__ = [
    # View & Adapter Contracts
    "IGraphView",
    "IGraphAdapter",
    # Index Contracts
    "IIndex",
    "IIndexBuilder",
    "IIndexRegistry",
    "IIndexFactory",
    "IIndexLifecycle",
    "IIndexStatistics",
    "IIndexValidator",
    "IIndexMetadata",
    "IIndexDescriptor",
    "IIndexProvider",
    # Planner Infrastructure Contracts
    "IPlannerCapabilities",
    "IPlannerDiagnostics",
    "IPlannerContext",
    "IPlannerSession",
    "IPlannerLifecycle",
    "IPlannerRegistry",
    "IQueryPlanner",
    # General Query Engine Contracts
    "ICapabilityRegistry",
    "ICapabilityValidator",
    "IQueryEngineAPI",
    "IQueryBudgetManager",
    "IQueryDiagnostics",
    "IQueryExtension",
    "IQueryContext",
    "IQueryExecutor",
    "IQueryPipeline",
    "ITraversalRegistry",
    "ITraversalStrategy",
    "IQueryValidator",
]
