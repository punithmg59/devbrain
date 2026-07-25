"""
core/symbol_identity/registry.py
---------------------------------
Multi-Language Symbol Normalizer Plugin Registry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor import RawSymbol
from core.symbol_identity.ids import generate_canonical_symbol_id
from core.symbol_identity.models import CanonicalSymbol
from core.symbol_identity.normalizer import LanguageSymbolNormalizer, QualifiedNameNormalizer
from core.symbols import Language, SymbolOrigin, SymbolVersion


class AbstractLanguageNormalizer(ABC):
    """
    Abstract interface for language-specific declaration normalizers.
    """

    @abstractmethod
    def normalize(
        self,
        raw_symbol: RawSymbol,
        tree: NamespaceTree,
        repository_id: str,
        overload_index: int = 0
    ) -> CanonicalSymbol:
        """
        Convert a RawSymbol into a CanonicalSymbol.
        """
        pass


class DefaultLanguageNormalizer(AbstractLanguageNormalizer):
    """
    Default Language Normalizer for Python and standard languages.
    """

    def normalize(
        self,
        raw_symbol: RawSymbol,
        tree: NamespaceTree,
        repository_id: str,
        overload_index: int = 0
    ) -> CanonicalSymbol:
        ns_node = tree.get_node(raw_symbol.namespace_id)
        canonical_fqn = QualifiedNameNormalizer.normalize_fqn(
            candidate_fqn=raw_symbol.qualified_name_candidate,
            symbol_name=raw_symbol.name,
            namespace_node=ns_node
        )

        overload_disc = f"overload_{overload_index}" if overload_index > 0 else None

        sym_id = generate_canonical_symbol_id(
            repository_id=repository_id,
            language=raw_symbol.language,
            fqn=canonical_fqn,
            kind=raw_symbol.kind,
            overload_discriminator=overload_disc
        )

        vis = LanguageSymbolNormalizer.normalize_visibility(raw_symbol)
        acc = LanguageSymbolNormalizer.normalize_accessibility(raw_symbol)
        mods = LanguageSymbolNormalizer.normalize_modifiers(raw_symbol)

        return CanonicalSymbol(
            id=sym_id,
            fqn=canonical_fqn,
            name=raw_symbol.name,
            kind=raw_symbol.kind,
            namespace_id=raw_symbol.namespace_id,
            language=raw_symbol.language,
            repository_id=repository_id,
            file_id=raw_symbol.file_id,
            file_path=raw_symbol.file_path,
            visibility=vis,
            accessibility=acc,
            modifiers=mods,
            source_info=raw_symbol.source_info,
            doc=raw_symbol.doc,
            attributes=raw_symbol.attributes,
            origin=SymbolOrigin(),
            version=SymbolVersion(),
            metadata=raw_symbol.metadata,
            raw_symbol_ref=raw_symbol.temp_id,
            parser_node_ref=raw_symbol.parser_node_ref
        )


class LanguageNormalizerRegistry:
    """
    Plugin Registry for language-specific normalizers.
    """
    _normalizers: Dict[Language, AbstractLanguageNormalizer] = {
        Language.PYTHON: DefaultLanguageNormalizer()
    }

    @classmethod
    def register(cls, language: Language, normalizer: AbstractLanguageNormalizer) -> None:
        cls._normalizers[language] = normalizer

    @classmethod
    def get_normalizer(cls, language: Language) -> AbstractLanguageNormalizer:
        return cls._normalizers.get(language, DefaultLanguageNormalizer())
