"""
Strongly-Typed Entity Reference AST Nodes.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.types import (
    FileId,
    NamespaceId,
    NodeId,
    PackageId,
    RepositoryId,
    SymbolId,
)


class EntityReference(BaseModel):
    """
    Base immutable AST reference to a code entity or graph node.
    """
    model_config = ConfigDict(frozen=True)

    reference_type: str = Field(..., description="Entity reference type discriminator")
    identifier: str = Field(..., description="Unique entity identifier string")
    name: Optional[str] = Field(default=None, description="Human readable display name")
    qualified_name: Optional[str] = Field(default=None, description="Fully qualified entity name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata key-value pairs")

    def to_node_id(self) -> NodeId:
        """Converts reference identifier to a NodeId."""
        return NodeId(self.identifier)


class SymbolReference(EntityReference):
    """Reference to a code symbol."""
    reference_type: str = Field(default="SYMBOL", description="Discriminator for symbol reference")
    symbol_id: Optional[SymbolId] = Field(default=None, description="Typed SymbolId reference")
    kind: Optional[str] = Field(default=None, description="Symbol kind (FUNCTION, CLASS, VARIABLE, etc.)")


class FileReference(EntityReference):
    """Reference to a source file."""
    reference_type: str = Field(default="FILE", description="Discriminator for file reference")
    file_id: Optional[FileId] = Field(default=None, description="Typed FileId reference")
    language: Optional[str] = Field(default=None, description="Source programming language")


class PackageReference(EntityReference):
    """Reference to a package / dependency module."""
    reference_type: str = Field(default="PACKAGE", description="Discriminator for package reference")
    package_id: Optional[PackageId] = Field(default=None, description="Typed PackageId reference")
    version: Optional[str] = Field(default=None, description="Package version constraint string")


class NamespaceReference(EntityReference):
    """Reference to a code namespace."""
    reference_type: str = Field(default="NAMESPACE", description="Discriminator for namespace reference")
    namespace_id: Optional[NamespaceId] = Field(default=None, description="Typed NamespaceId reference")


class ModuleReference(EntityReference):
    """Reference to a code module."""
    reference_type: str = Field(default="MODULE", description="Discriminator for module reference")


class ClassReference(EntityReference):
    """Reference to a class definition."""
    reference_type: str = Field(default="CLASS", description="Discriminator for class reference")
    base_classes: tuple[str, ...] = Field(default_factory=tuple, description="Qualified names of base classes")


class FunctionReference(EntityReference):
    """Reference to a function or method."""
    reference_type: str = Field(default="FUNCTION", description="Discriminator for function reference")
    signature: Optional[str] = Field(default=None, description="Function signature string")


class InterfaceReference(EntityReference):
    """Reference to an interface or protocol contract."""
    reference_type: str = Field(default="INTERFACE", description="Discriminator for interface reference")


class ApiRouteReference(EntityReference):
    """Reference to an HTTP API route endpoint."""
    reference_type: str = Field(default="API_ROUTE", description="Discriminator for API route reference")
    http_method: Optional[str] = Field(default=None, description="HTTP verb (GET, POST, PUT, DELETE, etc.)")
    route_path: Optional[str] = Field(default=None, description="API route path template")


class RepositoryReference(EntityReference):
    """Reference to a codebase repository."""
    reference_type: str = Field(default="REPOSITORY", description="Discriminator for repository reference")
    repository_id: Optional[RepositoryId] = Field(default=None, description="Typed RepositoryId reference")


class CrossRepositoryReference(EntityReference):
    """Reference to a remote cross-repository code entity."""
    reference_type: str = Field(default="CROSS_REPOSITORY", description="Discriminator for cross-repo reference")
    target_repository_id: RepositoryId = Field(..., description="Target remote repository ID")
    target_entity_identifier: str = Field(..., description="Target remote entity identifier")


__all__ = [
    "EntityReference",
    "SymbolReference",
    "FileReference",
    "PackageReference",
    "NamespaceReference",
    "ModuleReference",
    "ClassReference",
    "FunctionReference",
    "InterfaceReference",
    "ApiRouteReference",
    "RepositoryReference",
    "CrossRepositoryReference",
]
