"""
core/inheritance_edges/resolver.py
----------------------------------
Multi-Language Base Type & Interface Resolver Engine.
"""

from __future__ import annotations

import hashlib
from typing import Optional
from pydantic import BaseModel, Field

from core.inheritance_edges.extractor import ExtractedInheritanceStatement
from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID, SymbolKind


class InheritanceResolutionResult(BaseModel):
    """
    Resolution outcome for an extracted inheritance statement.
    """
    target_symbol_id: SymbolID = Field(..., description="Resolved SymbolID or synthetic unresolved SymbolID")
    is_resolved: bool = Field(..., description="True if bound to an internal repository symbol")
    is_external: bool = Field(default=False, description="True if base class is an external library/framework type")
    is_interface: bool = Field(default=False, description="True if relationship is interface implementation")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Resolution confidence score")
    resolved_fqn: Optional[str] = Field(default=None, description="Resolved canonical QualifiedName string")
    resolution_strategy: str = Field(..., description="Name of resolution strategy applied")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class InheritanceResolver:
    """
    Resolves extracted inheritance statements against SemanticRepository SymbolTable.
    """

    def resolve_base_type(
        self,
        stmt: ExtractedInheritanceStatement,
        repo: SemanticRepository
    ) -> InheritanceResolutionResult:
        repo_id = repo.repository_id
        base_raw = stmt.base_type_raw.strip()

        # 1. Candidate FQNs
        candidate_fqns = [
            f"{repo_id}.{base_raw}",
            base_raw,
            f"{repo_id}.src.{base_raw}"
        ]

        if "/" in stmt.source_file_path or "\\" in stmt.source_file_path:
            clean_path = stmt.source_file_path.replace("\\", "/")
            dir_parts = clean_path.rsplit("/", 1)[0].split("/")
            dir_prefix = ".".join(dir_parts)
            candidate_fqns.append(f"{repo_id}.{dir_prefix}.{base_raw}")

        # Strategy 1: Exact QualifiedName Match
        for candidate in candidate_fqns:
            sym = repo.get_by_fqn(candidate)
            if sym and sym.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT):
                is_iface = stmt.is_interface or (sym.kind == SymbolKind.INTERFACE)
                return InheritanceResolutionResult(
                    target_symbol_id=sym.id,
                    is_resolved=True,
                    is_external=False,
                    is_interface=is_iface,
                    confidence=1.0,
                    resolved_fqn=sym.fqn.to_string(),
                    resolution_strategy="exact_fqn_match"
                )

        # Strategy 2: Same File Class Lookup
        file_syms = repo.get_symbols_in_file(stmt.source_file_path)
        for s in file_syms:
            if s.name == base_raw and s.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT):
                is_iface = stmt.is_interface or (s.kind == SymbolKind.INTERFACE)
                return InheritanceResolutionResult(
                    target_symbol_id=s.id,
                    is_resolved=True,
                    is_external=False,
                    is_interface=is_iface,
                    confidence=1.0,
                    resolved_fqn=s.fqn.to_string(),
                    resolution_strategy="same_file_class_match"
                )

        # Strategy 3: Simple Name Unique Match in Repository
        by_name_syms = [
            s for s in repo.symbol_table.get_by_name(base_raw)
            if s.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT)
        ]
        if len(by_name_syms) == 1:
            target = by_name_syms[0]
            is_iface = stmt.is_interface or (target.kind == SymbolKind.INTERFACE)
            return InheritanceResolutionResult(
                target_symbol_id=target.id,
                is_resolved=True,
                is_external=False,
                is_interface=is_iface,
                confidence=0.9,
                resolved_fqn=target.fqn.to_string(),
                resolution_strategy="simple_name_unique_match"
            )

        # Strategy 4: Fallback Unresolved External Base Class
        unresolved_id = self._generate_unresolved_symbol_id(repo_id, base_raw)
        return InheritanceResolutionResult(
            target_symbol_id=unresolved_id,
            is_resolved=False,
            is_external=True,
            is_interface=stmt.is_interface,
            confidence=0.5,
            resolved_fqn=base_raw,
            resolution_strategy="unresolved_external"
        )

    def _generate_unresolved_symbol_id(self, repository_id: str, base_raw: str) -> SymbolID:
        seed = f"{repository_id}::unresolved_base::{base_raw}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return SymbolID(value=f"sym_{digest}")
