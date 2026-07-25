"""
core/import_edges/resolver.py
------------------------------
Multi-Language Import Symbol Resolver Engine.
"""

from __future__ import annotations

import hashlib
from typing import Optional
from pydantic import BaseModel, Field

from core.import_edges.extractor import ExtractedImportStatement
from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID


class ImportResolutionResult(BaseModel):
    """
    Resolution outcome for an extracted import statement.
    """
    target_symbol_id: SymbolID = Field(..., description="Resolved SymbolID or synthetic unresolved SymbolID")
    is_resolved: bool = Field(..., description="True if bound to an internal repository symbol")
    is_external: bool = Field(default=False, description="True if target is an external library/dependency")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Resolution confidence score")
    resolved_fqn: Optional[str] = Field(default=None, description="Resolved canonical QualifiedName string")
    resolution_strategy: str = Field(..., description="Name of resolution strategy applied")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class ImportResolver:
    """
    Resolves extracted import statements against SemanticRepository SymbolTable.
    """

    def resolve_import(
        self,
        stmt: ExtractedImportStatement,
        repo: SemanticRepository
    ) -> ImportResolutionResult:
        repo_id = repo.repository_id
        target_raw = stmt.imported_target_raw.strip()

        # 1. Construct candidate FQNs
        candidate_fqns = [
            f"{repo_id}.{target_raw}",
            target_raw,
            f"{repo_id}.src.{target_raw}"
        ]

        if "/" in stmt.source_file_path or "\\" in stmt.source_file_path:
            clean_path = stmt.source_file_path.replace("\\", "/")
            dir_parts = clean_path.rsplit("/", 1)[0].split("/")
            dir_prefix = ".".join(dir_parts)
            candidate_fqns.append(f"{repo_id}.{dir_prefix}.{target_raw}")

        # Strategy 1: Exact QualifiedName Match
        for candidate in candidate_fqns:
            sym = repo.get_by_fqn(candidate)
            if sym:
                return ImportResolutionResult(
                    target_symbol_id=sym.id,
                    is_resolved=True,
                    is_external=False,
                    confidence=1.0,
                    resolved_fqn=sym.fqn.to_string(),
                    resolution_strategy="exact_fqn_match"
                )

        # Strategy 2: Relative Import Resolution
        if stmt.is_relative:
            rel_fqn = self._resolve_relative_fqn(stmt, repo_id)
            if rel_fqn:
                sym = repo.get_by_fqn(rel_fqn)
                if sym:
                    return ImportResolutionResult(
                        target_symbol_id=sym.id,
                        is_resolved=True,
                        is_external=False,
                        confidence=1.0,
                        resolved_fqn=sym.fqn.to_string(),
                        resolution_strategy="relative_depth_match"
                    )

        # Strategy 3: Prefix Parent Module Match
        if "." in target_raw:
            parent_target = target_raw.rsplit(".", 1)[0]
            parent_candidate = f"{repo_id}.{parent_target}"
            parent_sym = repo.get_by_fqn(parent_candidate)
            if parent_sym:
                return ImportResolutionResult(
                    target_symbol_id=parent_sym.id,
                    is_resolved=True,
                    is_external=False,
                    confidence=0.9,
                    resolved_fqn=parent_sym.fqn.to_string(),
                    resolution_strategy="module_prefix_match"
                )

        # Strategy 4: Fallback Unresolved External Import
        unresolved_id = self._generate_unresolved_symbol_id(repo_id, target_raw)
        return ImportResolutionResult(
            target_symbol_id=unresolved_id,
            is_resolved=False,
            is_external=True,
            confidence=0.5,
            resolved_fqn=target_raw,
            resolution_strategy="unresolved_external"
        )

    def _resolve_relative_fqn(self, stmt: ExtractedImportStatement, repository_id: str) -> Optional[str]:
        parts = stmt.source_file_path.replace("\\", "/").split("/")
        if len(parts) <= stmt.relative_level:
            return None
        base_parts = parts[:-stmt.relative_level]
        if stmt.imported_target_raw:
            base_parts.append(stmt.imported_target_raw)
        mod_str = ".".join(base_parts).rstrip(".py").rstrip(".ts").rstrip(".js")
        return f"{repository_id}.{mod_str}"

    def _generate_unresolved_symbol_id(self, repository_id: str, target_raw: str) -> SymbolID:
        seed = f"{repository_id}::unresolved_import::{target_raw}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return SymbolID(value=f"sym_{digest}")
