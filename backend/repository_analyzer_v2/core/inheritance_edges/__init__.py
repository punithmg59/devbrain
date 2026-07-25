"""
core/inheritance_edges Package
------------------------------
Inheritance Edge Builder for DevBrain Dependency Graph Platform.
"""

from core.inheritance_edges.builder import InheritanceEdgeBuilder
from core.inheritance_edges.diagnostics import (
    InheritanceDiagnostic,
    InheritanceEdgeDiagnostics,
)
from core.inheritance_edges.exceptions import (
    InheritanceBuilderError,
    InheritanceResolutionError,
    InheritanceSerializationError,
    InheritanceValidationError,
)
from core.inheritance_edges.extractor import (
    ExtractedInheritanceStatement,
    InheritanceExtractor,
)
from core.inheritance_edges.interfaces import IInheritanceEdgeBuilderFacade
from core.inheritance_edges.resolver import (
    InheritanceResolutionResult,
    InheritanceResolver,
)
from core.inheritance_edges.serialization import (
    INHERITANCE_EDGE_COLLECTION_VERSION,
    dict_to_inheritance_collection,
    hash_inheritance_collection,
    inheritance_collection_to_dict,
    inheritance_collection_to_json,
    json_to_inheritance_collection,
)
from core.inheritance_edges.statistics import InheritanceEdgeStatistics
from core.inheritance_edges.validator import InheritanceEdgeValidator

__all__ = [
    # Facade & Extractor/Resolver
    "InheritanceEdgeBuilder",
    "InheritanceExtractor",
    "InheritanceResolver",
    "ExtractedInheritanceStatement",
    "InheritanceResolutionResult",
    "InheritanceEdgeStatistics",
    # Diagnostics & Validation
    "InheritanceDiagnostic",
    "InheritanceEdgeDiagnostics",
    "InheritanceEdgeValidator",
    # Interfaces
    "IInheritanceEdgeBuilderFacade",
    # Exceptions
    "InheritanceBuilderError",
    "InheritanceResolutionError",
    "InheritanceValidationError",
    "InheritanceSerializationError",
    # Serialization
    "INHERITANCE_EDGE_COLLECTION_VERSION",
    "inheritance_collection_to_dict",
    "dict_to_inheritance_collection",
    "inheritance_collection_to_json",
    "json_to_inheritance_collection",
    "hash_inheritance_collection",
]
