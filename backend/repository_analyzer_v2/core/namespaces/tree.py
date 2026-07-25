"""
core/namespaces/tree.py
-----------------------
NamespaceTree Data Structure & Indexing Container.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from pydantic import BaseModel, Field, field_validator

from core.namespaces.diagnostics import NamespaceDiagnostics
from core.namespaces.enums import NamespaceKind
from core.namespaces.exceptions import NamespaceValidationError
from core.namespaces.models import NamespaceNode
from core.symbols.ids import NamespaceID
from core.symbols.qualified_name import QualifiedName

NAMESPACE_TREE_VERSION = "3.2.0"


class NamespaceTreeStatistics(BaseModel):
    """Execution and structure metrics for NamespaceTree."""
    total_nodes: int = Field(default=0, ge=0)
    max_depth: int = Field(default=0, ge=0)
    total_files: int = Field(default=0, ge=0)
    node_counts_by_kind: Dict[str, int] = Field(default_factory=dict)

    model_config = {
        "frozen": True
    }


class NamespaceTree(BaseModel):
    """
    Canonical, Immutable NamespaceTree hierarchy container.
    
    Serves as the frozen contract produced by Step 3.2 and consumed by Step 3.3.
    """
    repository_id: str = Field(..., description="Repository identifier")
    root_id: NamespaceID = Field(..., description="Root Repository NamespaceID")
    nodes: Dict[NamespaceID, NamespaceNode] = Field(
        default_factory=dict,
        description="ID to NamespaceNode mapping index"
    )
    fqn_index: Dict[str, NamespaceID] = Field(
        default_factory=dict,
        description="QualifiedName string to NamespaceID mapping"
    )
    file_index: Dict[str, List[NamespaceID]] = Field(
        default_factory=dict,
        description="File path to ordered NamespaceIDs mapping"
    )
    diagnostics: NamespaceDiagnostics = Field(
        default_factory=NamespaceDiagnostics,
        description="Recorded execution diagnostics report"
    )

    @field_validator("nodes", mode="before")
    @classmethod
    def _validate_nodes(cls, v: Any) -> Any:
        if isinstance(v, dict):
            new_dict = {}
            for k, val in v.items():
                key_obj = NamespaceID(value=k) if isinstance(k, str) else k
                new_dict[key_obj] = val
            return new_dict
        return v

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True
    }

    def get_node(self, id: NamespaceID) -> Optional[NamespaceNode]:
        """Fetch a NamespaceNode by its NamespaceID."""
        return self.nodes.get(id)

    def get_by_fqn(self, fqn: str | QualifiedName) -> Optional[NamespaceNode]:
        """Fetch a NamespaceNode by its QualifiedName string or object."""
        fqn_str = fqn.to_string() if isinstance(fqn, QualifiedName) else str(fqn)
        node_id = self.fqn_index.get(fqn_str)
        return self.nodes.get(node_id) if node_id else None

    def get_nodes_by_file(self, file_path: str) -> List[NamespaceNode]:
        """Fetch all NamespaceNodes declared within a specific file."""
        ids = self.file_index.get(file_path, [])
        return [self.nodes[nid] for nid in ids if nid in self.nodes]

    def get_parent(self, id: NamespaceID) -> Optional[NamespaceNode]:
        """Fetch the immediate parent NamespaceNode of a node."""
        node = self.nodes.get(id)
        if node and node.parent_id:
            return self.nodes.get(node.parent_id)
        return None

    def get_children(self, id: NamespaceID) -> List[NamespaceNode]:
        """Fetch immediate child NamespaceNodes of a node in declaration order."""
        node = self.nodes.get(id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_ancestors(self, id: NamespaceID) -> List[NamespaceNode]:
        """Fetch all ancestor NamespaceNodes from parent up to repository root."""
        ancestors: List[NamespaceNode] = []
        current = self.get_parent(id)
        while current:
            ancestors.append(current)
            current = self.get_parent(current.id)
        return ancestors

    def get_descendants(self, id: NamespaceID) -> List[NamespaceNode]:
        """Fetch all descendant NamespaceNodes via DFS traversal."""
        descendants: List[NamespaceNode] = []
        for child in self.get_children(id):
            descendants.append(child)
            descendants.extend(self.get_descendants(child.id))
        return descendants

    def get_siblings(self, id: NamespaceID) -> List[NamespaceNode]:
        """Fetch sibling NamespaceNodes sharing the same parent."""
        parent = self.get_parent(id)
        if not parent:
            return []
        return [self.nodes[cid] for cid in parent.children_ids if cid != id and cid in self.nodes]

    def traverse_dfs(self, start_id: Optional[NamespaceID] = None) -> Iterator[NamespaceNode]:
        """Depth-First Search iterator over namespace tree nodes."""
        target_id = start_id or self.root_id
        root_node = self.nodes.get(target_id)
        if not root_node:
            return

        stack = [root_node]
        visited: Set[NamespaceID] = set()

        while stack:
            current = stack.pop()
            if current.id in visited:
                continue
            visited.add(current.id)
            yield current

            # Push children in reverse order so leftmost child is processed first
            for cid in reversed(current.children_ids):
                if cid in self.nodes and cid not in visited:
                    stack.append(self.nodes[cid])

    def traverse_bfs(self, start_id: Optional[NamespaceID] = None) -> Iterator[NamespaceNode]:
        """Breadth-First Search iterator over namespace tree nodes."""
        target_id = start_id or self.root_id
        root_node = self.nodes.get(target_id)
        if not root_node:
            return

        queue = deque([root_node])
        visited: Set[NamespaceID] = {root_node.id}

        while queue:
            current = queue.popleft()
            yield current

            for cid in current.children_ids:
                if cid in self.nodes and cid not in visited:
                    visited.add(cid)
                    queue.append(self.nodes[cid])

    def get_statistics(self) -> NamespaceTreeStatistics:
        """Compute execution statistics for the NamespaceTree."""
        total_nodes = len(self.nodes)
        total_files = len(self.file_index)
        kind_counts: Dict[str, int] = {}
        max_depth = 0

        for node in self.nodes.values():
            kind_str = node.kind.value
            kind_counts[kind_str] = kind_counts.get(kind_str, 0) + 1
            
            # Compute depth
            depth = len(self.get_ancestors(node.id))
            if depth > max_depth:
                max_depth = depth

        return NamespaceTreeStatistics(
            total_nodes=total_nodes,
            max_depth=max_depth,
            total_files=total_files,
            node_counts_by_kind=kind_counts
        )
