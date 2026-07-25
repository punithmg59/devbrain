"""
core/symbol_identity Package
-----------------------------
Canonical Symbol Identity Builder and CanonicalSymbolCollection for DevBrain.
"""

from core.symbol_identity.builder import (
    CanonicalSymbolCollection,
    SymbolIdentityBuilder,
)
from core.symbol_identity.diagnostics import (
    IdentityDiagnostic,
    IdentityDiagnostics,
)
from core.symbol_identity.exceptions import (
    DuplicateSymbolError,
    IdentityError,
    IdentitySerializationError,
    IdentityValidationError,
    NormalizationError,
)
from core.symbol_identity.ids import generate_canonical_symbol_id
from core.symbol_identity.interfaces import (
    ICanonicalSymbol,
    ICanonicalSymbolCollection,
    ISymbolIdentityBuilderFacade,
)
from core.symbol_identity.models import (
    CanonicalSymbol,
    CanonicalSymbolStatistics,
)
from core.symbol_identity.normalizer import (
    LanguageSymbolNormalizer,
    QualifiedNameNormalizer,
)
from core.symbol_identity.registry import (
    AbstractLanguageNormalizer,
    DefaultLanguageNormalizer,
    LanguageNormalizerRegistry,
)
from core.symbol_identity.serialization import (
    CANONICAL_SYMBOL_COLLECTION_VERSION,
    canonical_collection_to_dict,
    canonical_collection_to_json,
    dict_to_canonical_collection,
    hash_canonical_collection,
    json_to_canonical_collection,
)
from core.symbol_identity.validator import SymbolIdentityValidator

__all__ = [
    # Facade & Models
    "SymbolIdentityBuilder",
    "CanonicalSymbolCollection",
    "CanonicalSymbol",
    "CanonicalSymbolStatistics",
    # SymbolID Strategy
    "generate_canonical_symbol_id",
    # Diagnostics
    "IdentityDiagnostic",
    "IdentityDiagnostics",
    # Normalizers & Plugins
    "QualifiedNameNormalizer",
    "LanguageSymbolNormalizer",
    "AbstractLanguageNormalizer",
    "DefaultLanguageNormalizer",
    "LanguageNormalizerRegistry",
    # Validation
    "SymbolIdentityValidator",
    # Interfaces
    "ICanonicalSymbol",
    "ICanonicalSymbolCollection",
    "ISymbolIdentityBuilderFacade",
    # Exceptions
    "IdentityError",
    "DuplicateSymbolError",
    "NormalizationError",
    "IdentityValidationError",
    "IdentitySerializationError",
    # Serialization
    "CANONICAL_SYMBOL_COLLECTION_VERSION",
    "canonical_collection_to_dict",
    "dict_to_canonical_collection",
    "canonical_collection_to_json",
    "json_to_canonical_collection",
    "hash_canonical_collection",
]
