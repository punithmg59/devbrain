"""
core/symbol_extractor/models.py
--------------------------------
RawSymbol, TemporaryExtractionID, and RawSymbolCollection Domain Models.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator

from core.symbol_extractor.exceptions import SymbolExtractionValidationError, TemporaryIDError
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
    SymbolKind,
    Visibility,
)


class TemporaryExtractionID(BaseModel):
    """
    Deterministic Temporary Extraction Identifier for a discovered declaration.
    
    Format: 'tmp_sym_<24-character-sha256-hex>'
    """
    value: str = Field(..., description="Temporary extraction identifier string")

    model_config = {
        "frozen": True
    }

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, v: Any) -> str:
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        v_str = str(v)
        if not v_str or not v_str.startswith("tmp_sym_"):
            raise TemporaryIDError(f"TemporaryExtractionID must start with 'tmp_sym_'. Got: '{v}'")
        return v_str

    def __str__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TemporaryExtractionID):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False


def generate_temporary_id(
    repository_id: str,
    file_path: str,
    namespace_id: Union[NamespaceID, str],
    name: str,
    kind: Union[SymbolKind, str],
    declaration_order: int = 0
) -> TemporaryExtractionID:
    """
    Generate a deterministic, collision-resistant TemporaryExtractionID.
    """
    nid_str = namespace_id.value if isinstance(namespace_id, NamespaceID) else str(namespace_id)
    kind_str = kind.value if isinstance(kind, SymbolKind) else str(kind).lower()

    seed = f"{repository_id.strip()}::{file_path.strip()}::{nid_str}::{name.strip()}::{kind_str}::{declaration_order}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return TemporaryExtractionID(value=f"tmp_sym_{digest}")


class RawSymbol(BaseModel):
    """
    Canonical Immutable representation of a Raw Discovered Symbol declaration.
    """
    temp_id: TemporaryExtractionID = Field(..., description="Temporary extraction identifier")
    kind: SymbolKind = Field(..., description="Canonical SymbolKind classification")
    name: str = Field(..., description="Unqualified simple declaration name")
    qualified_name_candidate: QualifiedName = Field(..., description="Candidate QualifiedName")
    namespace_id: NamespaceID = Field(..., description="Containing NamespaceID from NamespaceTree")
    language: Language = Field(..., description="Source programming language")
    repository_id: str = Field(..., description="Identifier of containing repository")
    file_id: str = Field(..., description="Identifier of source file")
    file_path: str = Field(..., description="Repository-relative file path")
    parser_result_id: str = Field(..., description="Identifier of ParserResult triggering extraction")
    source_info: SourceInformation = Field(..., description="Source range location provenance")
    declaration_order: int = Field(default=0, ge=0, description="Order of declaration within parent file/scope")
    visibility: Visibility = Field(default_factory=Visibility, description="Visibility classification")
    accessibility: Accessibility = Field(default_factory=Accessibility, description="Accessibility permissions")
    modifiers: ModifierSet = Field(default_factory=ModifierSet, description="Modifiers set")
    doc: Optional[Documentation] = Field(default=None, description="Extracted docstring/documentation")
    attributes: List[Attribute] = Field(default_factory=list, description="Decorators and annotations")
    type_annotation: Optional[str] = Field(default=None, description="Type annotation string if declared")
    parser_node_ref: Optional[Dict[str, Any]] = Field(default=None, description="Raw parser AST node reference")
    metadata: Metadata = Field(default_factory=Metadata, description="Extensible metadata container")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise SymbolExtractionValidationError("RawSymbol name cannot be empty.")
        return v.strip()


class SymbolExtractionStatistics(BaseModel):
    """Execution metrics captured during symbol extraction."""
    total_symbols: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0.0)
    symbols_by_kind: Dict[str, int] = Field(default_factory=dict)
    symbols_by_language: Dict[str, int] = Field(default_factory=dict)

    model_config = {
        "frozen": True
    }
