"""
Unit tests verifying that all protocol contracts import cleanly and can be type-checked.
"""

from graph_query_engine.api import IQueryEngineAPI
from graph_query_engine.budget import IQueryBudgetManager
from graph_query_engine.capabilities import ICapabilityRegistry, ICapabilityValidator
from graph_query_engine.config import ConfigurationLoader, ConfigurationValidator
from graph_query_engine.diagnostics import IQueryDiagnostics
from graph_query_engine.extension import IQueryExtension
from graph_query_engine.index import IIndex, IIndexRegistry
from graph_query_engine.lifecycle import LifecycleComponent
from graph_query_engine.logging import Logger, LoggerFactory
from graph_query_engine.model import IQueryContext
from graph_query_engine.pipeline import IQueryExecutor, IQueryPipeline
from graph_query_engine.planner import IQueryPlanner
from graph_query_engine.shared import (
    ComponentFactory,
    ComponentProvider,
    Disposable,
    ServiceRegistry,
)
from graph_query_engine.traversal import ITraversalRegistry, ITraversalStrategy
from graph_query_engine.validation import IQueryValidator
from graph_query_engine.view import IGraphView


def test_contracts_importable():
    """
    Verifies that all 17 public placeholder and infrastructure contracts import cleanly.
    """
    contracts = [
        IGraphView,
        IQueryPipeline,
        IQueryExecutor,
        IQueryPlanner,
        ITraversalStrategy,
        ITraversalRegistry,
        IIndex,
        IIndexRegistry,
        IQueryContext,
        IQueryBudgetManager,
        ICapabilityRegistry,
        ICapabilityValidator,
        IQueryDiagnostics,
        IQueryEngineAPI,
        IQueryExtension,
        IQueryValidator,
        ConfigurationLoader,
        ConfigurationValidator,
        LifecycleComponent,
        Logger,
        LoggerFactory,
        ComponentProvider,
        ComponentFactory,
        ServiceRegistry,
        Disposable,
    ]
    assert len(contracts) == 25
    for contract in contracts:
        assert contract is not None
