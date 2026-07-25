"""
core/call_edges/resolver.py
----------------------------
Multi-Language Callee Symbol Resolver Engine.
"""

from __future__ import annotations

import hashlib
from typing import Optional
from pydantic import BaseModel, Field

from core.call_edges.extractor import ExtractedCallStatement
from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID, SymbolKind


class CallResolutionResult(BaseModel):
    """
    Resolution outcome for an extracted call statement.
    """
    target_symbol_id: SymbolID = Field(..., description="Resolved SymbolID or synthetic unresolved SymbolID")
    is_resolved: bool = Field(..., description="True if bound to an internal repository symbol")
    is_external: bool = Field(default=False, description="True if target is an external library or unparsed function")
    is_recursive: bool = Field(default=False, description="True if caller invokes itself")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Resolution confidence score")
    resolved_fqn: Optional[str] = Field(default=None, description="Resolved canonical QualifiedName string")
    resolution_strategy: str = Field(..., description="Name of resolution strategy applied")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class CallResolver:
    """
    Resolves extracted call statements against SemanticRepository SymbolTable.
    """

    def resolve_callee(
        self,
        stmt: ExtractedCallStatement,
        repo: SemanticRepository
    ) -> CallResolutionResult:
        repo_id = repo.repository_id
        callee_expr = stmt.callee_expression_raw.strip()
        callee_name = stmt.callee_name.strip()
        caller_sym = repo.get_symbol(stmt.caller_symbol_id)

        # Strategy 1: Exact QualifiedName Match
        candidate_fqn = f"{repo_id}.{callee_expr}"
        sym = repo.get_by_fqn(candidate_fqn) or repo.get_by_fqn(callee_expr)
        if sym:
            is_rec = (sym.id == stmt.caller_symbol_id)
            return CallResolutionResult(
                target_symbol_id=sym.id,
                is_resolved=True,
                is_external=False,
                is_recursive=is_rec,
                confidence=1.0,
                resolved_fqn=sym.fqn.to_string(),
                resolution_strategy="exact_fqn_match"
            )

        # Strategy 2: Enclosing Class Method Match (self / this calls)
        if caller_sym and stmt.receiver_expression in ("self", "this"):
            ns_syms = repo.symbol_table.get_namespace_symbols(caller_sym.namespace_id)
            for s in ns_syms:
                if s.name == callee_name and s.kind in (SymbolKind.METHOD, SymbolKind.FUNCTION):
                    is_rec = (s.id == stmt.caller_symbol_id)
                    return CallResolutionResult(
                        target_symbol_id=s.id,
                        is_resolved=True,
                        is_external=False,
                        is_recursive=is_rec,
                        confidence=1.0,
                        resolved_fqn=s.fqn.to_string(),
                        resolution_strategy="enclosing_class_method_match"
                    )

        # Strategy 3: Same File Function/Method Match
        file_syms = repo.get_symbols_in_file(stmt.source_file_path)
        for s in file_syms:
            if s.name == callee_name and s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                is_rec = (s.id == stmt.caller_symbol_id)
                return CallResolutionResult(
                    target_symbol_id=s.id,
                    is_resolved=True,
                    is_external=False,
                    is_recursive=is_rec,
                    confidence=0.95,
                    resolved_fqn=s.fqn.to_string(),
                    resolution_strategy="same_file_function_match"
                )

        # Strategy 4: Simple Name Unique Match in Repository
        by_name_syms = [
            s for s in repo.symbol_table.get_by_name(callee_name)
            if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
        ]
        if len(by_name_syms) == 1:
            target = by_name_syms[0]
            is_rec = (target.id == stmt.caller_symbol_id)
            return CallResolutionResult(
                target_symbol_id=target.id,
                is_resolved=True,
                is_external=False,
                is_recursive=is_rec,
                confidence=0.85,
                resolved_fqn=target.fqn.to_string(),
                resolution_strategy="simple_name_unique_match"
            )

        # Strategy 5: Fallback Unresolved External Call
        unresolved_id = self._generate_unresolved_symbol_id(repo_id, callee_expr)
        return CallResolutionResult(
            target_symbol_id=unresolved_id,
            is_resolved=False,
            is_external=True,
            is_recursive=False,
            confidence=0.5,
            resolved_fqn=callee_expr,
            resolution_strategy="unresolved_external"
        )

    def _generate_unresolved_symbol_id(self, repository_id: str, callee_expr: str) -> SymbolID:
        seed = f"{repository_id}::unresolved_call::{callee_expr}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return SymbolID(value=f"sym_{digest}")
