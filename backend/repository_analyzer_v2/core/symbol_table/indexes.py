"""
core/symbol_table/indexes.py
-----------------------------
Multi-Index Container and Lookup Architecture for SymbolTable.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field, field_validator

from core.symbol_identity import CanonicalSymbol
from core.symbols import Language, SymbolID, SymbolKind, VisibilityKind
from core.symbols.ids import NamespaceID


class SymbolIndexSet(BaseModel):
    """
    Immutable Container storing 11 multi-dimensional lookup indexes for Canonical Symbols.
    """
    by_id: Dict[SymbolID, CanonicalSymbol] = Field(
        default_factory=dict,
        description="O(1) SymbolID to CanonicalSymbol index"
    )
    by_fqn: Dict[str, CanonicalSymbol] = Field(
        default_factory=dict,
        description="O(1) QualifiedName string to CanonicalSymbol index"
    )
    by_name: Dict[str, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="Simple unqualified name to CanonicalSymbols index"
    )
    by_namespace: Dict[NamespaceID, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="Containing NamespaceID to CanonicalSymbols index"
    )
    by_repository: Dict[str, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="RepositoryID to CanonicalSymbols index"
    )
    by_file: Dict[str, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="File path to CanonicalSymbols index"
    )
    by_language: Dict[Language, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="Language to CanonicalSymbols index"
    )
    by_kind: Dict[SymbolKind, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="SymbolKind to CanonicalSymbols index"
    )
    by_visibility: Dict[VisibilityKind, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="VisibilityKind to CanonicalSymbols index"
    )
    by_parent_namespace: Dict[NamespaceID, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="Parent NamespaceID to child CanonicalSymbols index"
    )
    by_child_namespace: Dict[NamespaceID, List[CanonicalSymbol]] = Field(
        default_factory=dict,
        description="Child NamespaceID to contained CanonicalSymbols index"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("by_id", mode="before")
    @classmethod
    def _validate_by_id_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = SymbolID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    @field_validator("by_namespace", "by_parent_namespace", "by_child_namespace", mode="before")
    @classmethod
    def _validate_ns_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = NamespaceID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v
