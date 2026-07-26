"""
Unified Public Contracts Package for Graph Query Engine.

Centralizes all public Protocol contracts exposed by the Graph Query Engine.
"""

from graph_query_engine.contracts.api import IQueryEngineAPI
from graph_query_engine.contracts.budget import IQueryBudgetManager
from graph_query_engine.contracts.capabilities import (
    ICapabilityRegistry,
    ICapabilityValidator,
)
from graph_query_engine.contracts.diagnostics import IQueryDiagnostics
from graph_query_engine.contracts.extension import IQueryExtension
from graph_query_engine.contracts.index import IIndex, IIndexRegistry
from graph_query_engine.contracts.model import IQueryContext
from graph_query_engine.contracts.pipeline import IQueryExecutor, IQueryPipeline
from graph_query_engine.contracts.planner import IQueryPlanner
from graph_query_engine.contracts.traversal import (
    ITraversalRegistry,
    ITraversalStrategy,
)
from graph_query_engine.contracts.validation import IQueryValidator
from graph_query_engine.contracts.view import IGraphView

__all__ = [
    "IGraphView",
    "IQueryPipeline",
    "IQueryExecutor",
    "IQueryPlanner",
    "ITraversalStrategy",
    "ITraversalRegistry",
    "IIndex",
    "IIndexRegistry",
    "IQueryContext",
    "IQueryBudgetManager",
    "ICapabilityRegistry",
    "ICapabilityValidator",
    "IQueryDiagnostics",
    "IQueryEngineAPI",
    "IQueryExtension",
    "IQueryValidator",
]
