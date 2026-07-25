"""
core/dependency_graph Package
------------------------------
Primary Dependency Graph Builder for DevBrain Dependency Graph Platform.
"""

from core.dependency_graph.builder import DependencyGraphBuilder
from core.dependency_graph.diagnostics import (
    DependencyGraphDiagnostics,
    GraphDiagnostic,
)
from core.dependency_graph.exceptions import (
    GraphBuilderError,
    GraphSerializationError,
    GraphValidationError,
)
from core.dependency_graph.graph import DependencyGraph
from core.dependency_graph.indexes import DependencyGraphIndexes
from core.dependency_graph.interfaces import (
    IDependencyGraph,
    IDependencyGraphBuilderFacade,
)
from core.dependency_graph.serialization import (
    DEPENDENCY_GRAPH_VERSION,
    dependency_graph_to_dict,
    dependency_graph_to_json,
    dict_to_dependency_graph,
    hash_dependency_graph,
    json_to_dependency_graph,
)
from core.dependency_graph.statistics import DependencyGraphStatistics
from core.dependency_graph.validator import DependencyGraphValidator

__all__ = [
    # Facade & Main Graph Domain Model
    "DependencyGraphBuilder",
    "DependencyGraph",
    "DependencyGraphIndexes",
    "DependencyGraphStatistics",
    # Diagnostics & Validation
    "GraphDiagnostic",
    "DependencyGraphDiagnostics",
    "DependencyGraphValidator",
    # Interfaces
    "IDependencyGraph",
    "IDependencyGraphBuilderFacade",
    # Exceptions
    "GraphBuilderError",
    "GraphValidationError",
    "GraphSerializationError",
    # Serialization
    "DEPENDENCY_GRAPH_VERSION",
    "dependency_graph_to_dict",
    "dict_to_dependency_graph",
    "dependency_graph_to_json",
    "json_to_dependency_graph",
    "hash_dependency_graph",
]
