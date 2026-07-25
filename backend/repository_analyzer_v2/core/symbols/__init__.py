"""
core/symbols Package
--------------------
Canonical, Language-Independent Immutable Symbol Model for DevBrain.
"""

from core.symbols.enums import (
    AccessibilityKind,
    DocumentationFormat,
    Language,
    ModifierKind,
    OriginKind,
    RelationshipKind,
    SymbolKind,
    VarianceKind,
    VisibilityKind,
)
from core.symbols.exceptions import (
    QualifiedNameError,
    SymbolError,
    SymbolIDError,
    SymbolSerializationError,
    SymbolValidationError,
)
from core.symbols.ids import (
    NamespaceID,
    SymbolID,
    generate_namespace_id,
    generate_symbol_id,
)
from core.symbols.interfaces import IQualifiedName, ISymbol, ISymbolID
from core.symbols.metadata import (
    Annotation,
    Attribute,
    Documentation,
    Metadata,
    SymbolOrigin,
    SymbolOwner,
    SymbolVersion,
)
from core.symbols.models import (
    GenericParameter,
    SourceInformation,
    SourceLocation,
    SourceRange,
    Symbol,
    SymbolRelationship,
    TypeParameter,
    TypeReference,
)
from core.symbols.modifiers import ModifierSet
from core.symbols.qualified_name import QualifiedName
from core.symbols.serialization import (
    SYMBOL_MODEL_VERSION,
    are_symbols_equal,
    dict_to_symbol,
    hash_symbol,
    json_to_symbol,
    symbol_to_dict,
    symbol_to_json,
)
from core.symbols.visibility import Accessibility, Visibility

__all__ = [
    # Models
    "Symbol",
    "SourceLocation",
    "SourceRange",
    "SourceInformation",
    "TypeReference",
    "GenericParameter",
    "TypeParameter",
    "SymbolRelationship",
    # Enums
    "Language",
    "SymbolKind",
    "VisibilityKind",
    "AccessibilityKind",
    "ModifierKind",
    "RelationshipKind",
    "DocumentationFormat",
    "OriginKind",
    "VarianceKind",
    # IDs
    "SymbolID",
    "NamespaceID",
    "generate_symbol_id",
    "generate_namespace_id",
    # Qualified Name
    "QualifiedName",
    # Visibility & Modifiers
    "Visibility",
    "Accessibility",
    "ModifierSet",
    # Metadata
    "Documentation",
    "Attribute",
    "Annotation",
    "SymbolOrigin",
    "SymbolOwner",
    "SymbolVersion",
    "Metadata",
    # Interfaces
    "ISymbol",
    "ISymbolID",
    "IQualifiedName",
    # Exceptions
    "SymbolError",
    "SymbolIDError",
    "QualifiedNameError",
    "SymbolValidationError",
    "SymbolSerializationError",
    # Serialization
    "SYMBOL_MODEL_VERSION",
    "symbol_to_dict",
    "dict_to_symbol",
    "symbol_to_json",
    "json_to_symbol",
    "hash_symbol",
    "are_symbols_equal",
]
