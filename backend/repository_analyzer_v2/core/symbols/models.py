"""
core/symbols/models.py
----------------------
Canonical Symbol Domain Models for the DevBrain Dependency Graph Platform.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator

from core.symbols.enums import (
    AccessibilityKind,
    Language,
    ModifierKind,
    RelationshipKind,
    SymbolKind,
    VarianceKind,
    VisibilityKind,
)
from core.symbols.exceptions import SymbolValidationError
from core.symbols.ids import SymbolID
from core.symbols.metadata import (
    Annotation,
    Attribute,
    Documentation,
    Metadata,
    SymbolOrigin,
    SymbolOwner,
    SymbolVersion,
)
from core.symbols.modifiers import ModifierSet
from core.symbols.qualified_name import QualifiedName
from core.symbols.visibility import Accessibility, Visibility


class SourceLocation(BaseModel):
    """
    Source code text coordinates.
    """
    line: int = Field(..., ge=1, description="1-indexed line number")
    column: int = Field(..., ge=0, description="0-indexed column offset")
    offset: int = Field(default=0, ge=0, description="0-indexed byte offset in file")

    model_config = {
        "frozen": True
    }


class SourceRange(BaseModel):
    """
    Source code span bounded by start and end locations.
    """
    start: SourceLocation = Field(..., description="Start coordinate")
    end: SourceLocation = Field(..., description="End coordinate")
    byte_length: int = Field(default=0, ge=0, description="Byte length of range")

    model_config = {
        "frozen": True
    }

    @field_validator("end")
    @classmethod
    def _validate_end(cls, v: SourceLocation, info: Any) -> SourceLocation:
        start = info.data.get("start")
        if start and (v.line < start.line or (v.line == start.line and v.column < start.column)):
            raise SymbolValidationError(
                f"End location ({v.line}:{v.column}) cannot precede start location ({start.line}:{start.column})"
            )
        return v


class SourceInformation(BaseModel):
    """
    Complete source code provenance for a Symbol.
    """
    file_id: str = Field(..., description="Canonical file identifier")
    file_path: str = Field(..., description="Repository-relative file path")
    range: SourceRange = Field(..., description="Source code range span")
    parser_node_ref: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parser AST node metadata (e.g. tree-sitter node type)"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class TypeReference(BaseModel):
    """
    Language-independent Type Reference model.
    """
    name: str = Field(..., description="Type name identifier (e.g. 'List', 'HashMap', 'int')")
    raw_type: str = Field(..., description="Original raw type signature string")
    qualified_name: Optional[QualifiedName] = Field(default=None, description="Resolved QualifiedName of type if available")
    is_generic: bool = Field(default=False, description="True if type has generic arguments")
    type_arguments: List[TypeReference] = Field(default_factory=list, description="Generic type parameters")
    is_nullable: bool = Field(default=False, description="True if type is optional/nullable")
    is_array: bool = Field(default=False, description="True if array or slice type")
    is_pointer: bool = Field(default=False, description="True if pointer or reference type")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class GenericParameter(BaseModel):
    """
    Generic type parameter declaration model.
    """
    name: str = Field(..., description="Generic parameter name (e.g. 'T', 'K', 'V')")
    constraint: Optional[TypeReference] = Field(default=None, description="Upper bound / interface constraint")
    bounds: List[TypeReference] = Field(default_factory=list, description="Multiple type bounds")
    default_type: Optional[TypeReference] = Field(default=None, description="Default type if omitted")
    variance: VarianceKind = Field(default=VarianceKind.INVARIANT, description="Type parameter variance")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


# TypeParameter alias
TypeParameter = GenericParameter


class SymbolRelationship(BaseModel):
    """
    Metadata-only representation of a relationship between symbols.
    
    NOTE: Does NOT implement resolution logic, AST traversal, or graph building.
    """
    relationship_kind: RelationshipKind = Field(..., description="Semantic relationship type")
    source_symbol_id: SymbolID = Field(..., description="SymbolID of relationship source")
    target_symbol_id: Optional[SymbolID] = Field(default=None, description="SymbolID of relationship target if known")
    target_fqn: Optional[QualifiedName] = Field(default=None, description="QualifiedName of relationship target if known")
    location: Optional[SourceLocation] = Field(default=None, description="Source location of the relationship reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible relationship metadata")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


class Symbol(BaseModel):
    """
    Canonical, Language-Independent Immutable Symbol Model for DevBrain.
    
    This is the core domain contract frozen across the Dependency Graph Platform.
    """
    id: SymbolID = Field(..., description="Deterministic, unique symbol identifier")
    fqn: QualifiedName = Field(..., description="Fully Qualified Name of symbol")
    name: str = Field(..., description="Unqualified simple symbol identifier name")
    kind: SymbolKind = Field(..., description="Canonical SymbolKind classification")
    language: Language = Field(..., description="Programming language source of symbol")
    visibility: Visibility = Field(default_factory=Visibility, description="Visibility level")
    accessibility: Accessibility = Field(default_factory=Accessibility, description="Accessibility permissions")
    modifiers: ModifierSet = Field(default_factory=ModifierSet, description="Immutable set of modifiers")
    source_info: SourceInformation = Field(..., description="Source location provenance")
    doc: Optional[Documentation] = Field(default=None, description="Structured documentation strings")
    annotations: List[Annotation] = Field(default_factory=list, description="Annotations and decorators")
    type_ref: Optional[TypeReference] = Field(default=None, description="Associated type signature if applicable")
    generic_params: List[GenericParameter] = Field(default_factory=list, description="Generic parameters list")
    owner: SymbolOwner = Field(default_factory=SymbolOwner, description="Owner scope information")
    origin: SymbolOrigin = Field(default_factory=SymbolOrigin, description="Symbol origin provenance")
    version: SymbolVersion = Field(default_factory=SymbolVersion, description="Symbol content versioning")
    metadata: Metadata = Field(default_factory=Metadata, description="Extensible non-identity metadata")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise SymbolValidationError("Symbol name cannot be empty.")
        return v.strip()

    def compute_content_hash(self) -> str:
        """
        Compute SHA-256 content digest of semantic symbol declaration.
        Excludes volatile non-semantic metadata.
        """
        raw_seed = f"{self.id.value}::{self.fqn.to_string()}::{self.kind.value}::{self.language.value}::{self.name}"
        return hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()
