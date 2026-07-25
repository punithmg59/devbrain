"""
core/symbol_identity/models.py
-------------------------------
CanonicalSymbol and CanonicalSymbolCollection Domain Models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from core.symbol_extractor import TemporaryExtractionID
from core.symbol_identity.diagnostics import IdentityDiagnostics
from core.symbol_identity.exceptions import IdentityValidationError
from core.symbols import (
    Accessibility,
    Attribute,
    Documentation,
    Language,
    Metadata,
    ModifierSet,
    NamespaceID,
    QualifiedName,
    SourceInformation,
    SymbolID,
    SymbolKind,
    SymbolOrigin,
    SymbolVersion,
    Visibility,
)


class CanonicalSymbol(BaseModel):
    """
    Canonical Immutable Symbol Entity with deterministic SymbolID and normalized QualifiedName.
    """
    id: SymbolID = Field(..., description="Deterministic, unique canonical symbol identifier")
    fqn: QualifiedName = Field(..., description="Final normalized Fully Qualified Name")
    name: str = Field(..., description="Simple unqualified symbol identifier name")
    kind: SymbolKind = Field(..., description="Canonical SymbolKind classification")
    namespace_id: NamespaceID = Field(..., description="Containing NamespaceID from NamespaceTree")
    language: Language = Field(..., description="Source programming language")
    repository_id: str = Field(..., description="Identifier of containing repository")
    file_id: str = Field(..., description="Identifier of source file")
    file_path: str = Field(..., description="Repository-relative file path")
    visibility: Visibility = Field(default_factory=Visibility, description="Visibility classification")
    accessibility: Accessibility = Field(default_factory=Accessibility, description="Accessibility permissions")
    modifiers: ModifierSet = Field(default_factory=ModifierSet, description="Modifiers set")
    source_info: SourceInformation = Field(..., description="Source code range location provenance")
    doc: Optional[Documentation] = Field(default=None, description="Extracted docstring/documentation")
    attributes: List[Attribute] = Field(default_factory=list, description="Decorators and annotations")
    origin: SymbolOrigin = Field(default_factory=SymbolOrigin, description="Symbol origin provenance")
    version: SymbolVersion = Field(default_factory=SymbolVersion, description="Symbol content versioning")
    metadata: Metadata = Field(default_factory=Metadata, description="Extensible non-identity metadata")
    raw_symbol_ref: Optional[TemporaryExtractionID] = Field(default=None, description="TemporaryExtractionID reference from Step 3.3")
    parser_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise IdentityValidationError("CanonicalSymbol name cannot be empty.")
        return v.strip()


class CanonicalSymbolStatistics(BaseModel):
    """Execution metrics captured during symbol identity building."""
    total_canonical_symbols: int = Field(default=0, ge=0)
    duplicates_detected: int = Field(default=0, ge=0)
    overloads_detected: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0.0)

    model_config = {
        "frozen": True
    }
