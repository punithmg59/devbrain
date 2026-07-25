"""
core/symbol_extractor Package
-----------------------------
Canonical Symbol Extractor & RawSymbolCollection for DevBrain.
"""

from core.symbol_extractor.diagnostics import (
    SymbolExtractionDiagnostic,
    SymbolExtractionDiagnostics,
)
from core.symbol_extractor.exceptions import (
    ExtractorRegistryError,
    SymbolExtractionError,
    SymbolExtractionSerializationError,
    SymbolExtractionValidationError,
    TemporaryIDError,
)
from core.symbol_extractor.extractor import RawSymbolCollection, SymbolExtractor
from core.symbol_extractor.interfaces import (
    IRawSymbol,
    IRawSymbolCollection,
    ISymbolExtractorFacade,
)
from core.symbol_extractor.models import (
    RawSymbol,
    SymbolExtractionStatistics,
    TemporaryExtractionID,
    generate_temporary_id,
)
from core.symbol_extractor.python_extractor import PythonSymbolExtractor
from core.symbol_extractor.registry import (
    AbstractSymbolExtractor,
    GenericFallbackSymbolExtractor,
    SymbolExtractorRegistry,
)
from core.symbol_extractor.serialization import (
    RAW_SYMBOL_COLLECTION_VERSION,
    collection_to_dict,
    collection_to_json,
    dict_to_collection,
    hash_collection,
    json_to_collection,
)
from core.symbol_extractor.tree_integration import NamespaceResolver
from core.symbol_extractor.validator import SymbolExtractionValidator

__all__ = [
    # Facade & Models
    "SymbolExtractor",
    "RawSymbolCollection",
    "RawSymbol",
    "TemporaryExtractionID",
    "generate_temporary_id",
    "SymbolExtractionStatistics",
    # Diagnostics
    "SymbolExtractionDiagnostic",
    "SymbolExtractionDiagnostics",
    # Extractor Framework & Python
    "AbstractSymbolExtractor",
    "PythonSymbolExtractor",
    "GenericFallbackSymbolExtractor",
    "SymbolExtractorRegistry",
    # Tree Integration & Validation
    "NamespaceResolver",
    "SymbolExtractionValidator",
    # Interfaces
    "IRawSymbol",
    "IRawSymbolCollection",
    "ISymbolExtractorFacade",
    # Exceptions
    "SymbolExtractionError",
    "TemporaryIDError",
    "SymbolExtractionValidationError",
    "ExtractorRegistryError",
    "SymbolExtractionSerializationError",
    # Serialization
    "RAW_SYMBOL_COLLECTION_VERSION",
    "collection_to_dict",
    "dict_to_collection",
    "collection_to_json",
    "json_to_collection",
    "hash_collection",
]
