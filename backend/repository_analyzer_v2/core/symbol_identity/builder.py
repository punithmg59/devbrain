"""
core/symbol_identity/builder.py
--------------------------------
SymbolIdentityBuilder Facade Engine and CanonicalSymbolCollection Container.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from core.namespaces.tree import NamespaceTree
from core.symbol_extractor import RawSymbolCollection
from core.symbol_identity.diagnostics import IdentityDiagnostics
from core.symbol_identity.models import CanonicalSymbol, CanonicalSymbolStatistics
from core.symbol_identity.registry import LanguageNormalizerRegistry
from core.symbol_identity.validator import SymbolIdentityValidator
from core.symbols import QualifiedName, SymbolID
from core.symbols.ids import NamespaceID


class CanonicalSymbolCollection(BaseModel):
    """
    Canonical, Immutable CanonicalSymbolCollection container.
    
    Serves as the frozen contract produced by Step 3.4 and consumed by Step 3.5.
    """
    repository_id: str = Field(..., description="Repository identifier")
    symbols: List[CanonicalSymbol] = Field(default_factory=list, description="Canonical symbols list")
    symbols_by_id: Dict[SymbolID, CanonicalSymbol] = Field(
        default_factory=dict,
        description="SymbolID to CanonicalSymbol index"
    )
    symbols_by_fqn: Dict[str, SymbolID] = Field(
        default_factory=dict,
        description="QualifiedName string to SymbolID mapping"
    )
    symbols_by_namespace: Dict[NamespaceID, List[SymbolID]] = Field(
        default_factory=dict,
        description="NamespaceID to SymbolIDs mapping"
    )
    symbols_by_file: Dict[str, List[SymbolID]] = Field(
        default_factory=dict,
        description="File path to SymbolIDs mapping"
    )
    statistics: CanonicalSymbolStatistics = Field(
        default_factory=CanonicalSymbolStatistics,
        description="Identity build statistics"
    )
    diagnostics: IdentityDiagnostics = Field(
        default_factory=IdentityDiagnostics,
        description="Identity build diagnostics report"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("symbols_by_id", mode="before")
    @classmethod
    def _validate_by_id_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = SymbolID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    @field_validator("symbols_by_namespace", mode="before")
    @classmethod
    def _validate_by_ns_keys(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = NamespaceID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    def get_symbol(self, id: SymbolID) -> Optional[CanonicalSymbol]:
        """Fetch a CanonicalSymbol by its SymbolID."""
        return self.symbols_by_id.get(id)

    def get_by_fqn(self, fqn: str | QualifiedName) -> Optional[CanonicalSymbol]:
        """Fetch a CanonicalSymbol by its QualifiedName string or object."""
        fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn)
        sym_id = self.symbols_by_fqn.get(fqn_str)
        return self.symbols_by_id.get(sym_id) if sym_id else None

    def get_symbols_in_namespace(self, namespace_id: NamespaceID) -> List[CanonicalSymbol]:
        """Fetch all CanonicalSymbols declared in a specific NamespaceID."""
        sym_ids = self.symbols_by_namespace.get(namespace_id, [])
        return [self.symbols_by_id[sid] for sid in sym_ids if sid in self.symbols_by_id]

    def get_symbols_in_file(self, file_path: str) -> List[CanonicalSymbol]:
        """Fetch all CanonicalSymbols declared within a specific file."""
        sym_ids = self.symbols_by_file.get(file_path, [])
        return [self.symbols_by_id[sid] for sid in sym_ids if sid in self.symbols_by_id]


class SymbolIdentityBuilder:
    """
    Facade engine that converts RawSymbolCollection into a CanonicalSymbolCollection.
    """

    def build_canonical_symbols(
        self,
        raw_collection: RawSymbolCollection,
        tree: NamespaceTree
    ) -> CanonicalSymbolCollection:
        """
        Main Facade Entrypoint.
        """
        start_time = time.perf_counter()
        repository_id = raw_collection.repository_id
        canonical_list: List[CanonicalSymbol] = []
        diagnostics = IdentityDiagnostics()

        by_id: Dict[SymbolID, CanonicalSymbol] = {}
        by_fqn: Dict[str, SymbolID] = {}
        by_ns: Dict[NamespaceID, List[SymbolID]] = {}
        by_file: Dict[str, List[SymbolID]] = {}

        seen_fqn_counts: Dict[str, int] = {}
        duplicates_count = 0
        overloads_count = 0

        for raw_sym in raw_collection.symbols:
            try:
                # Track overload count for FQN candidate
                candidate_fqn_str = raw_sym.qualified_name_candidate.to_string()
                overload_idx = seen_fqn_counts.get(candidate_fqn_str, 0)
                seen_fqn_counts[candidate_fqn_str] = overload_idx + 1

                if overload_idx > 0:
                    overloads_count += 1

                normalizer = LanguageNormalizerRegistry.get_normalizer(raw_sym.language)
                can_sym = normalizer.normalize(
                    raw_symbol=raw_sym,
                    tree=tree,
                    repository_id=repository_id,
                    overload_index=overload_idx
                )

                canonical_list.append(can_sym)
                by_id[can_sym.id] = can_sym
                
                fqn_str = can_sym.fqn.to_string()
                if fqn_str in by_fqn:
                    duplicates_count += 1
                else:
                    by_fqn[fqn_str] = can_sym.id

                by_ns.setdefault(can_sym.namespace_id, []).append(can_sym.id)
                by_file.setdefault(can_sym.file_path, []).append(can_sym.id)

            except Exception as e:
                diagnostics = diagnostics.add_error(
                    message=f"Error generating identity for symbol '{raw_sym.name}': {str(e)}",
                    file_path=raw_sym.file_path,
                    code="ERR_IDENTITY_BUILD_FAILED"
                )

        # Integrity & Duplicate Validation
        val_diags = SymbolIdentityValidator.validate(canonical_list, tree, repository_id)
        if val_diags.diagnostics:
            all_diags = diagnostics.diagnostics + val_diags.diagnostics
            diagnostics = IdentityDiagnostics(diagnostics=all_diags)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        stats = CanonicalSymbolStatistics(
            total_canonical_symbols=len(canonical_list),
            duplicates_detected=duplicates_count,
            overloads_detected=overloads_count,
            duration_ms=duration_ms
        )

        return CanonicalSymbolCollection(
            repository_id=repository_id,
            symbols=canonical_list,
            symbols_by_id=by_id,
            symbols_by_fqn=by_fqn,
            symbols_by_namespace=by_ns,
            symbols_by_file=by_file,
            statistics=stats,
            diagnostics=diagnostics
        )
