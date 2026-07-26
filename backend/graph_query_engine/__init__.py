"""
Graph Query Engine - Deterministic Graph Access Layer for DevBrain.

Enterprise Hardened Step 1 & Step 1.1 Foundation.
"""

from graph_query_engine.config import (
    DefaultConfig,
    EnvironmentConfiguration,
    GraphQueryEngineConfig,
)
from graph_query_engine.constants import ENGINE_NAME, ENGINE_VERSION
from graph_query_engine.contracts import (
    ICapabilityRegistry,
    ICapabilityValidator,
    IGraphView,
    IIndex,
    IIndexRegistry,
    IQueryBudgetManager,
    IQueryContext,
    IQueryDiagnostics,
    IQueryEngineAPI,
    IQueryExecutor,
    IQueryExtension,
    IQueryPipeline,
    IQueryPlanner,
    ITraversalRegistry,
    ITraversalStrategy,
    IQueryValidator,
)
from graph_query_engine.core import (
    EngineExecutionContext,
    GraphQueryEngine,
    GraphQueryEngineBuilder,
    GraphQueryEngineFactory,
)
from graph_query_engine.errors import (
    ConfigurationError,
    ExecutionError,
    GraphQueryError,
    InitializationError,
    NotImplementedError,
    TimeoutError,
    ValidationError,
)
from graph_query_engine.lifecycle import EngineState, LifecycleComponent
from graph_query_engine.types import (
    CorrelationId,
    DependencyType,
    EdgeId,
    FileId,
    LanguageId,
    NamespaceId,
    NodeId,
    PackageId,
    QueryId,
    RelationshipType,
    RepositoryId,
    RequestId,
    SnapshotId,
    SymbolId,
    TraversalDirection,
)

__version__ = ENGINE_VERSION
__engine_name__ = ENGINE_NAME

__all__ = [
    # Metadata & Version
    "__version__",
    "__engine_name__",
    "ENGINE_NAME",
    "ENGINE_VERSION",
    # Core Infrastructure
    "GraphQueryEngine",
    "GraphQueryEngineFactory",
    "GraphQueryEngineBuilder",
    "EngineExecutionContext",
    # Configuration
    "GraphQueryEngineConfig",
    "DefaultConfig",
    "EnvironmentConfiguration",
    # Errors
    "GraphQueryError",
    "InitializationError",
    "ConfigurationError",
    "ValidationError",
    "ExecutionError",
    "TimeoutError",
    "NotImplementedError",
    # Lifecycle
    "EngineState",
    "LifecycleComponent",
    # Primitive Domain Types
    "NodeId",
    "EdgeId",
    "SymbolId",
    "FileId",
    "NamespaceId",
    "PackageId",
    "RepositoryId",
    "SnapshotId",
    "QueryId",
    "RequestId",
    "CorrelationId",
    "LanguageId",
    "TraversalDirection",
    "RelationshipType",
    "DependencyType",
    # Public Contracts Surface
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
