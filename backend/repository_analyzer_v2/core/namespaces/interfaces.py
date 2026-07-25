"""
core/namespaces/interfaces.py
-----------------------------
Public Interface Protocols for Namespace contracts.
"""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable

from core.namespaces.enums import NamespaceKind
from core.symbols.enums import Language
from core.symbols.ids import NamespaceID
from core.symbols.interfaces import IQualifiedName
from models.parser import ParserResult


@runtime_checkable
class INamespaceNode(Protocol):
    """Protocol for Namespace Nodes."""
    @property
    def id(self) -> NamespaceID: ...
    @property
    def fqn(self) -> IQualifiedName: ...
    @property
    def name(self) -> str: ...
    @property
    def kind(self) -> NamespaceKind: ...
    @property
    def language(self) -> Language: ...
    @property
    def parent_id(self) -> Optional[NamespaceID]: ...


@runtime_checkable
class INamespaceTree(Protocol):
    """Protocol for Namespace Tree containers."""
    @property
    def repository_id(self) -> str: ...
    @property
    def root_id(self) -> NamespaceID: ...
    def get_node(self, id: NamespaceID) -> Optional[INamespaceNode]: ...
    def get_by_fqn(self, fqn: str) -> Optional[INamespaceNode]: ...
    def get_children(self, id: NamespaceID) -> List[INamespaceNode]: ...


@runtime_checkable
class INamespaceBuilderFacade(Protocol):
    """Protocol for Namespace Builder Facade."""
    def build_tree(self, parser_results: List[ParserResult], repository_id: str) -> INamespaceTree: ...
