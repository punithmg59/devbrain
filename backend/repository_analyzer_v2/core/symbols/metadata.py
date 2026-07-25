"""
core/symbols/metadata.py
------------------------
Metadata, Documentation, Annotations, Attributes, Origin, Owner, and Version models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.symbols.enums import DocumentationFormat, OriginKind, SymbolKind
from core.symbols.ids import SymbolID
from core.symbols.qualified_name import QualifiedName


class Documentation(BaseModel):
    """
    Structured documentation metadata attached to a Symbol.
    """
    summary: str = Field(default="", description="Brief single-line summary")
    detailed_description: str = Field(default="", description="Full docstring content")
    doc_format: DocumentationFormat = Field(
        default=DocumentationFormat.PLAIN,
        description="Documentation markup format"
    )
    params: Dict[str, str] = Field(default_factory=dict, description="Parameter name to description mapping")
    returns: Optional[str] = Field(default=None, description="Return value description")
    throws: Dict[str, str] = Field(default_factory=dict, description="Exception type to description mapping")
    deprecation_reason: Optional[str] = Field(default=None, description="Reason for deprecation if applicable")

    model_config = {
        "frozen": True
    }


class Attribute(BaseModel):
    """
    Attribute / Decorator / Annotation definition attached to a Symbol.
    """
    name: str = Field(..., description="Attribute or decorator identifier name")
    qualified_name: Optional[QualifiedName] = Field(default=None, description="Qualified name of attribute type")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Parsed attribute arguments")
    raw_text: Optional[str] = Field(default=None, description="Raw source text of the annotation")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }


# Alias Annotation to Attribute for convenience
Annotation = Attribute


class SymbolOrigin(BaseModel):
    """
    Origin tracking for symbol declarations.
    """
    kind: OriginKind = Field(default=OriginKind.SOURCE, description="Origin classification of the symbol")
    source_tool: Optional[str] = Field(default=None, description="Tool name that extracted or generated the symbol")

    model_config = {
        "frozen": True
    }


class SymbolOwner(BaseModel):
    """
    Owner scope reference for a Symbol.
    """
    owner_id: Optional[SymbolID] = Field(default=None, description="SymbolID of containing owner")
    owner_fqn: Optional[QualifiedName] = Field(default=None, description="QualifiedName of containing owner")
    owner_kind: Optional[SymbolKind] = Field(default=None, description="SymbolKind of containing owner")

    model_config = {
        "frozen": True
    }


class SymbolVersion(BaseModel):
    """
    Semantic versioning metadata for symbols.
    """
    major: int = Field(default=1, ge=0)
    minor: int = Field(default=0, ge=0)
    patch: int = Field(default=0, ge=0)
    content_hash: Optional[str] = Field(default=None, description="SHA-256 digest of symbol definition content")

    model_config = {
        "frozen": True
    }


class Metadata(BaseModel):
    """
    Extensible metadata container.
    
    IMPORTANT: Changes to Metadata do NOT alter Symbol identity (SymbolID).
    """
    language_metadata: Dict[str, Any] = Field(default_factory=dict, description="Language-specific metadata")
    framework_metadata: Dict[str, Any] = Field(default_factory=dict, description="Framework-specific metadata")
    plugin_metadata: Dict[str, Any] = Field(default_factory=dict, description="Plugin-specific metadata")
    user_metadata: Dict[str, Any] = Field(default_factory=dict, description="User-defined metadata")
    ai_metadata: Dict[str, Any] = Field(default_factory=dict, description="AI agent semantic metadata")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    attributes: List[Attribute] = Field(default_factory=list, description="Extensible attributes list")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }
