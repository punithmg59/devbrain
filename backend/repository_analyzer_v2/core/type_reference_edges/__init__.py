"""
core/type_reference_edges Package
----------------------------------
Type Reference Edge Builder for DevBrain Dependency Graph Platform.
"""

from core.type_reference_edges.builder import TypeReferenceEdgeBuilder
from core.type_reference_edges.diagnostics import (
    TypeReferenceDiagnostic,
    TypeReferenceEdgeDiagnostics,
)
from core.type_reference_edges.exceptions import (
    TypeReferenceBuilderError,
    TypeReferenceResolutionError,
    TypeReferenceSerializationError,
    TypeReferenceValidationError,
)
from core.type_reference_edges.extractor import (
    ExtractedTypeReferenceStatement,
    TypeReferenceExtractor,
)
from core.type_reference_edges.interfaces import ITypeReferenceEdgeBuilderFacade
from core.type_reference_edges.resolver import (
    TypeReferenceResolutionResult,
    TypeReferenceResolver,
)
from core.type_reference_edges.serialization import (
    TYPE_REFERENCE_EDGE_COLLECTION_VERSION,
    dict_to_type_reference_collection,
    hash_type_reference_collection,
    json_to_type_reference_collection,
    type_reference_collection_to_dict,
    type_reference_collection_to_json,
)
from core.type_reference_edges.statistics import TypeReferenceEdgeStatistics
from core.type_reference_edges.validator import TypeReferenceEdgeValidator

__all__ = [
    # Facade & Extractor/Resolver
    "TypeReferenceEdgeBuilder",
    "TypeReferenceExtractor",
    "TypeReferenceResolver",
    "ExtractedTypeReferenceStatement",
    "TypeReferenceResolutionResult",
    "TypeReferenceEdgeStatistics",
    # Diagnostics & Validation
    "TypeReferenceDiagnostic",
    "TypeReferenceEdgeDiagnostics",
    "TypeReferenceEdgeValidator",
    # Interfaces
    "ITypeReferenceEdgeBuilderFacade",
    # Exceptions
    "TypeReferenceBuilderError",
    "TypeReferenceResolutionError",
    "TypeReferenceValidationError",
    "TypeReferenceSerializationError",
    # Serialization
    "TYPE_REFERENCE_EDGE_COLLECTION_VERSION",
    "type_reference_collection_to_dict",
    "dict_to_type_reference_collection",
    "type_reference_collection_to_json",
    "json_to_type_reference_collection",
    "hash_type_reference_collection",
]
