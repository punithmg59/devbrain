"""
core/type_reference_edges/resolver.py
--------------------------------------
Multi-Language Type Symbol Resolver Engine.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from pydantic import BaseModel, Field

from core.symbol_builder import SemanticRepository
from core.symbols import SymbolID, SymbolKind
from core.type_reference_edges.extractor import ExtractedTypeReferenceStatement


class TypeReferenceResolutionResult(BaseModel):
    """
    Resolution outcome for an extracted type reference statement.
    """
    target_symbol_id: SymbolID = Field(..., description="Resolved SymbolID or synthetic unresolved SymbolID")
    is_resolved: bool = Field(..., description="True if bound to an internal repository symbol")
    is_external: bool = Field(default=False, description="True if type is an external library/framework or primitive type")
    is_primitive: bool = Field(default=False, description="True if type is a primitive scalar type (int, str, bool, void)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Resolution confidence score")
    resolved_fqn: Optional[str] = Field(default=None, description="Resolved canonical QualifiedName string")
    resolution_strategy: str = Field(..., description="Name of resolution strategy applied")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class TypeReferenceResolver:
    """
    Resolves extracted type references against SemanticRepository SymbolTable.
    """

    PRIMITIVE_TYPES = {
        "int", "float", "str", "string", "bool", "boolean", "void", "bytes",
        "number", "any", "unknown", "never", "object", "dict", "list", "tuple",
        "set", "i32", "i64", "f32", "f64", "u32", "u64", "usize", "isize"
    }

    def resolve_type_symbol(
        self,
        stmt: ExtractedTypeReferenceStatement,
        repo: SemanticRepository
    ) -> TypeReferenceResolutionResult:
        repo_id = repo.repository_id
        type_raw = stmt.referenced_type_raw.strip()

        # Unwrap generic containers e.g. List[User], Promise<User>, Option<User>, *User
        type_clean = self._unwrap_generic_type(type_raw)

        # Check if primitive type
        if type_clean.lower() in self.PRIMITIVE_TYPES:
            unresolved_id = self._generate_unresolved_symbol_id(repo_id, type_clean)
            return TypeReferenceResolutionResult(
                target_symbol_id=unresolved_id,
                is_resolved=False,
                is_external=True,
                is_primitive=True,
                confidence=0.5,
                resolved_fqn=type_clean,
                resolution_strategy="primitive_type"
            )

        # 1. Candidate FQNs
        candidate_fqns = [
            f"{repo_id}.{type_clean}",
            type_clean,
            f"{repo_id}.src.{type_clean}"
        ]

        if "/" in stmt.source_file_path or "\\" in stmt.source_file_path:
            clean_path = stmt.source_file_path.replace("\\", "/")
            dir_parts = clean_path.rsplit("/", 1)[0].split("/")
            dir_prefix = ".".join(dir_parts)
            candidate_fqns.append(f"{repo_id}.{dir_prefix}.{type_clean}")

        # Strategy 1: Exact QualifiedName Match
        for candidate in candidate_fqns:
            sym = repo.get_by_fqn(candidate)
            if sym and sym.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT, SymbolKind.ENUM, SymbolKind.TYPE_ALIAS):
                return TypeReferenceResolutionResult(
                    target_symbol_id=sym.id,
                    is_resolved=True,
                    is_external=False,
                    is_primitive=False,
                    confidence=1.0,
                    resolved_fqn=sym.fqn.to_string(),
                    resolution_strategy="exact_fqn_match"
                )

        # Strategy 2: Same File Type Lookup
        file_syms = repo.get_symbols_in_file(stmt.source_file_path)
        for s in file_syms:
            if s.name == type_clean and s.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT, SymbolKind.ENUM, SymbolKind.TYPE_ALIAS):
                return TypeReferenceResolutionResult(
                    target_symbol_id=s.id,
                    is_resolved=True,
                    is_external=False,
                    is_primitive=False,
                    confidence=1.0,
                    resolved_fqn=s.fqn.to_string(),
                    resolution_strategy="same_file_type_match"
                )

        # Strategy 3: Simple Name Unique Match in Repository
        by_name_syms = [
            s for s in repo.symbol_table.get_by_name(type_clean)
            if s.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE, SymbolKind.STRUCT, SymbolKind.ENUM, SymbolKind.TYPE_ALIAS)
        ]
        if len(by_name_syms) == 1:
            target = by_name_syms[0]
            return TypeReferenceResolutionResult(
                target_symbol_id=target.id,
                is_resolved=True,
                is_external=False,
                is_primitive=False,
                confidence=0.9,
                resolved_fqn=target.fqn.to_string(),
                resolution_strategy="simple_name_unique_match"
            )

        # Strategy 4: Fallback Unresolved External Type
        unresolved_id = self._generate_unresolved_symbol_id(repo_id, type_clean)
        return TypeReferenceResolutionResult(
            target_symbol_id=unresolved_id,
            is_resolved=False,
            is_external=True,
            is_primitive=False,
            confidence=0.5,
            resolved_fqn=type_clean,
            resolution_strategy="unresolved_external"
        )

    def _unwrap_generic_type(self, raw: str) -> str:
        s = raw.strip().lstrip("*&")
        match = re.search(r"[\[<]([A-Za-z0-9_.]+)[\]>]", s)
        if match:
            return match.group(1).strip()
        return s

    def _generate_unresolved_symbol_id(self, repository_id: str, type_name: str) -> SymbolID:
        seed = f"{repository_id}::unresolved_type::{type_name}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return SymbolID(value=f"sym_{digest}")
