"""
core/namespaces/models.py
-------------------------
Canonical NamespaceNode Domain Model.
"""

from __future__ import annotations

from typing import Optional, Tuple
from pydantic import BaseModel, Field, field_validator

from core.namespaces.enums import NamespaceKind
from core.namespaces.exceptions import NamespaceValidationError
from core.symbols.enums import Language
from core.symbols.ids import NamespaceID
from core.symbols.metadata import Metadata
from core.symbols.models import SourceInformation
from core.symbols.qualified_name import QualifiedName


class NamespaceNode(BaseModel):
    """
    Canonical, Immutable representation of a single Lexical Scope / Namespace Boundary.
    """
    id: NamespaceID = Field(..., description="Deterministic, unique namespace identifier")
    fqn: QualifiedName = Field(..., description="Fully Qualified Name of namespace boundary")
    name: str = Field(..., description="Simple unqualified name identifier")
    kind: NamespaceKind = Field(..., description="Namespace boundary kind classification")
    language: Language = Field(default=Language.FUTURE, description="Source programming language")
    repository_id: str = Field(..., description="Identifier of containing repository")
    file_id: Optional[str] = Field(default=None, description="Identifier of source file if file-bound")
    file_path: Optional[str] = Field(default=None, description="Repository-relative file path if file-bound")
    parent_id: Optional[NamespaceID] = Field(default=None, description="NamespaceID of parent scope node")
    children_ids: Tuple[NamespaceID, ...] = Field(default_factory=tuple, description="Ordered child namespace IDs")
    source_info: Optional[SourceInformation] = Field(default=None, description="Source code range span if applicable")
    declaration_order: int = Field(default=0, ge=0, description="Order of declaration within parent scope")
    metadata: Metadata = Field(default_factory=Metadata, description="Extensible metadata container")

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise NamespaceValidationError("Namespace name cannot be empty.")
        return v.strip()

    @property
    def is_root(self) -> bool:
        """True if node has no parent."""
        return self.parent_id is None

    def with_children(self, children: Tuple[NamespaceID, ...]) -> NamespaceNode:
        """Construct a new NamespaceNode instance with updated children IDs."""
        return NamespaceNode(
            id=self.id,
            fqn=self.fqn,
            name=self.name,
            kind=self.kind,
            language=self.language,
            repository_id=self.repository_id,
            file_id=self.file_id,
            file_path=self.file_path,
            parent_id=self.parent_id,
            children_ids=children,
            source_info=self.source_info,
            declaration_order=self.declaration_order,
            metadata=self.metadata
        )
