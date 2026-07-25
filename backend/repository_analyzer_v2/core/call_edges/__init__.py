"""
core/call_edges Package
-----------------------
Call Edge Builder for DevBrain Dependency Graph Platform.
"""

from core.call_edges.builder import CallEdgeBuilder
from core.call_edges.diagnostics import (
    CallDiagnostic,
    CallEdgeDiagnostics,
)
from core.call_edges.exceptions import (
    CallBuilderError,
    CallResolutionError,
    CallSerializationError,
    CallValidationError,
)
from core.call_edges.extractor import (
    CallExtractor,
    ExtractedCallStatement,
)
from core.call_edges.interfaces import ICallEdgeBuilderFacade
from core.call_edges.resolver import (
    CallResolutionResult,
    CallResolver,
)
from core.call_edges.serialization import (
    CALL_EDGE_COLLECTION_VERSION,
    call_collection_to_dict,
    call_collection_to_json,
    dict_to_call_collection,
    hash_call_collection,
    json_to_call_collection,
)
from core.call_edges.statistics import CallEdgeStatistics
from core.call_edges.validator import CallEdgeValidator

__all__ = [
    # Facade & Extractor/Resolver
    "CallEdgeBuilder",
    "CallExtractor",
    "CallResolver",
    "ExtractedCallStatement",
    "CallResolutionResult",
    "CallEdgeStatistics",
    # Diagnostics & Validation
    "CallDiagnostic",
    "CallEdgeDiagnostics",
    "CallEdgeValidator",
    # Interfaces
    "ICallEdgeBuilderFacade",
    # Exceptions
    "CallBuilderError",
    "CallResolutionError",
    "CallValidationError",
    "CallSerializationError",
    # Serialization
    "CALL_EDGE_COLLECTION_VERSION",
    "call_collection_to_dict",
    "dict_to_call_collection",
    "call_collection_to_json",
    "json_to_call_collection",
    "hash_call_collection",
]
