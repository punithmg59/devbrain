"""
core/namespaces Package
-----------------------
Canonical Namespace Builder and NamespaceTree Hierarchy for DevBrain.
"""

from core.namespaces.builder import NamespaceBuilder, NamespaceBuildOptions
from core.namespaces.diagnostics import NamespaceDiagnostic, NamespaceDiagnostics
from core.namespaces.enums import DiagnosticSeverity, NamespaceKind
from core.namespaces.exceptions import (
    NamespaceError,
    NamespaceIDError,
    NamespaceSerializationError,
    NamespaceTraversalError,
    NamespaceValidationError,
)
from core.namespaces.ids import generate_scope_namespace_id
from core.namespaces.interfaces import (
    INamespaceBuilderFacade,
    INamespaceNode,
    INamespaceTree,
)
from core.namespaces.models import NamespaceNode
from core.namespaces.serialization import (
    dict_to_tree,
    hash_tree,
    json_to_tree,
    tree_to_dict,
    tree_to_json,
)
from core.namespaces.traversal import (
    AbstractScopeExtractor,
    GenericFallbackScopeExtractor,
    PythonScopeExtractor,
    ScopeDefinition,
    ScopeExtractorRegistry,
)
from core.namespaces.tree import (
    NAMESPACE_TREE_VERSION,
    NamespaceTree,
    NamespaceTreeStatistics,
)
from core.namespaces.validator import NamespaceTreeValidator

__all__ = [
    # Facade & Options
    "NamespaceBuilder",
    "NamespaceBuildOptions",
    # Tree & Models
    "NamespaceNode",
    "NamespaceTree",
    "NamespaceTreeStatistics",
    # Enums
    "NamespaceKind",
    "DiagnosticSeverity",
    # Diagnostics
    "NamespaceDiagnostic",
    "NamespaceDiagnostics",
    # Scope Extractor Traversal
    "ScopeDefinition",
    "AbstractScopeExtractor",
    "PythonScopeExtractor",
    "GenericFallbackScopeExtractor",
    "ScopeExtractorRegistry",
    # Validation & IDs
    "NamespaceTreeValidator",
    "generate_scope_namespace_id",
    # Interfaces
    "INamespaceNode",
    "INamespaceTree",
    "INamespaceBuilderFacade",
    # Exceptions
    "NamespaceError",
    "NamespaceIDError",
    "NamespaceValidationError",
    "NamespaceTraversalError",
    "NamespaceSerializationError",
    # Serialization
    "NAMESPACE_TREE_VERSION",
    "tree_to_dict",
    "dict_to_tree",
    "tree_to_json",
    "json_to_tree",
    "hash_tree",
]
