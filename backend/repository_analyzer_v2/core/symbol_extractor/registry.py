"""
core/symbol_extractor/registry.py
----------------------------------
Language-Agnostic Symbol Extractor Registry & Abstract Plugin Interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor.models import RawSymbol
from core.symbols.enums import Language
from models.parser import ParserResult


class AbstractSymbolExtractor(ABC):
    """
    Abstract interface for language-specific AST Symbol Extractors.
    """

    @abstractmethod
    def extract(
        self,
        parser_result: ParserResult,
        tree: NamespaceTree,
        repository_id: str
    ) -> List[RawSymbol]:
        """
        Extract RawSymbols from a single ParserResult using the NamespaceTree for scope binding.
        """
        pass


class GenericFallbackSymbolExtractor(AbstractSymbolExtractor):
    """
    Fallback Symbol Extractor for generic or unhandled languages.
    Returns an empty list of RawSymbols.
    """

    def extract(
        self,
        parser_result: ParserResult,
        tree: NamespaceTree,
        repository_id: str
    ) -> List[RawSymbol]:
        return []


class SymbolExtractorRegistry:
    """
    Plugin Registry for language-specific Symbol Extractors.
    """
    _extractors: Dict[Language, AbstractSymbolExtractor] = {}

    @classmethod
    def register(cls, language: Language, extractor: AbstractSymbolExtractor) -> None:
        cls._extractors[language] = extractor

    @classmethod
    def get_extractor(cls, language: Language) -> AbstractSymbolExtractor:
        return cls._extractors.get(language, GenericFallbackSymbolExtractor())
