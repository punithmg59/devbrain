"""
core/import_edges Package
-------------------------
Import Edge Builder for DevBrain Dependency Graph Platform.
"""

from core.import_edges.builder import ImportEdgeBuilder
from core.import_edges.diagnostics import (
    ImportDiagnostic,
    ImportEdgeDiagnostics,
)
from core.import_edges.exceptions import (
    ImportBuilderError,
    ImportResolutionError,
    ImportSerializationError,
    ImportValidationError,
)
from core.import_edges.extractor import (
    ExtractedImportStatement,
    ImportExtractor,
)
from core.import_edges.interfaces import IImportEdgeBuilderFacade
from core.import_edges.resolver import (
    ImportResolutionResult,
    ImportResolver,
)
from core.import_edges.serialization import (
    IMPORT_EDGE_COLLECTION_VERSION,
    dict_to_import_collection,
    hash_import_collection,
    import_collection_to_dict,
    import_collection_to_json,
    json_to_import_collection,
)
from core.import_edges.statistics import ImportEdgeStatistics
from core.import_edges.validator import ImportEdgeValidator

__all__ = [
    # Facade & Extractor/Resolver
    "ImportEdgeBuilder",
    "ImportExtractor",
    "ImportResolver",
    "ExtractedImportStatement",
    "ImportResolutionResult",
    "ImportEdgeStatistics",
    # Diagnostics & Validation
    "ImportDiagnostic",
    "ImportEdgeDiagnostics",
    "ImportEdgeValidator",
    # Interfaces
    "IImportEdgeBuilderFacade",
    # Exceptions
    "ImportBuilderError",
    "ImportResolutionError",
    "ImportValidationError",
    "ImportSerializationError",
    # Serialization
    "IMPORT_EDGE_COLLECTION_VERSION",
    "import_collection_to_dict",
    "dict_to_import_collection",
    "import_collection_to_json",
    "json_to_import_collection",
    "hash_import_collection",
]
