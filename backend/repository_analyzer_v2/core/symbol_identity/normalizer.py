"""
core/symbol_identity/normalizer.py
-----------------------------------
QualifiedName and Language Symbol Normalization Utilities.
"""

from __future__ import annotations

from typing import Optional

from core.namespaces.models import NamespaceNode
from core.namespaces.tree import NamespaceTree
from core.symbol_extractor import RawSymbol
from core.symbols import Accessibility, ModifierSet, QualifiedName, Visibility


class QualifiedNameNormalizer:
    """
    Normalizes candidate QualifiedNames using NamespaceTree context.
    """

    @classmethod
    def normalize_fqn(
        cls,
        candidate_fqn: QualifiedName,
        symbol_name: str,
        namespace_node: Optional[NamespaceNode]
    ) -> QualifiedName:
        """
        Construct final canonical QualifiedName.
        If namespace_node is provided, ensures symbol_name is appended to namespace FQN.
        """
        if namespace_node:
            return namespace_node.fqn.child(symbol_name)
        return candidate_fqn


class LanguageSymbolNormalizer:
    """
    Standardizes language-specific declaration constructs into canonical Symbol properties.
    """

    @classmethod
    def normalize_visibility(cls, raw_symbol: RawSymbol) -> Visibility:
        """Normalize visibility modifiers."""
        if raw_symbol.visibility:
            return raw_symbol.visibility
        name = raw_symbol.name
        if name.startswith("_") and not name.startswith("__"):
            return Visibility.protected()
        if name.startswith("__") and not name.endswith("__"):
            return Visibility.private()
        return Visibility.public()

    @classmethod
    def normalize_accessibility(cls, raw_symbol: RawSymbol) -> Accessibility:
        """Normalize accessibility permissions."""
        return raw_symbol.accessibility or Accessibility.read_write()

    @classmethod
    def normalize_modifiers(cls, raw_symbol: RawSymbol) -> ModifierSet:
        """Normalize modifier sets."""
        return raw_symbol.modifiers or ModifierSet()
