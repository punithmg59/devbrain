"""
analysis/scope_resolution/scope_tree.py
----------------------------------------
Phase 4.5 — Scope Tree Container & Scope Lookup Engine.

Provides the canonical, thread-safe `ScopeTree` data structure for navigating
lexical scope hierarchies and performing scope-aware symbol lookups.

Design Principles
-----------------
- **Lexical Hierarchy Traversal**: Fast navigation across parent, children, ancestors,
  and descendant scopes.
- **O(depth) Symbol Lookup**: Scope-aware identifier search from target scope up to root.
- **Symbol-to-Scope Indexing**: O(1) reverse mapping from symbol_id to defining Scope.
- **Thread-Safe Read Access**: Immutable after resolution is complete.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from models.scope import Scope, ScopeMetrics
from models.symbol import Symbol
from analysis.symbol_table.symbol_table import SymbolTable


class ScopeTree(BaseModel):
    """
    Canonical lexical scope tree container for a repository or module.
    """

    tree_id: str = Field(
        default_factory=lambda: f"scopetree-{uuid.uuid4().hex[:12]}",
        description="Globally unique scope tree instance ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    scopes: Dict[str, Scope] = Field(
        default_factory=dict,
        description="Map of scope_id -> Scope object",
    )
    root_scope_ids: List[str] = Field(
        default_factory=list,
        description="IDs of root-level scopes (Module or Repository scopes)",
    )
    symbol_to_scope_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of symbol_id -> defining scope_id",
    )
    metrics: ScopeMetrics = Field(
        default_factory=ScopeMetrics,
        description="Scope telemetry and performance metrics",
    )

    def add_scope(self, scope: Scope) -> None:
        """Add a scope node to the tree and wire parent/child linkages."""
        self.scopes[scope.id] = scope

        if scope.parent_id is None:
            if scope.id not in self.root_scope_ids:
                self.root_scope_ids.append(scope.id)
        else:
            parent = self.scopes.get(scope.parent_id)
            if parent and scope.id not in parent.children_ids:
                parent.children_ids.append(scope.id)

        for sym_id in scope.defined_symbol_ids:
            self.symbol_to_scope_map[sym_id] = scope.id

    def get_scope(self, scope_id: str) -> Optional[Scope]:
        """Return `Scope` by ID, or None."""
        return self.scopes.get(scope_id)

    def get_parent_scope(self, scope_id: str) -> Optional[Scope]:
        """Return direct parent `Scope` for scope_id, or None."""
        scope = self.scopes.get(scope_id)
        if not scope or not scope.parent_id:
            return None
        return self.scopes.get(scope.parent_id)

    def get_children_scopes(self, scope_id: str) -> List[Scope]:
        """Return list of direct child `Scope` nodes for scope_id."""
        scope = self.scopes.get(scope_id)
        if not scope:
            return []
        return [
            self.scopes[cid]
            for cid in scope.children_ids
            if cid in self.scopes
        ]

    def get_ancestor_scopes(self, scope_id: str) -> List[Scope]:
        """Return list of ancestor scopes starting from immediate parent up to root."""
        ancestors: List[Scope] = []
        visited: Set[str] = set()
        curr_id = scope_id

        while curr_id:
            scope = self.scopes.get(curr_id)
            if not scope or not scope.parent_id:
                break
            pid = scope.parent_id
            if pid in visited:
                break  # Cycle detection
            visited.add(pid)
            parent = self.scopes.get(pid)
            if parent:
                ancestors.append(parent)
                curr_id = pid
            else:
                break

        return ancestors

    def get_descendant_scopes(self, scope_id: str) -> List[Scope]:
        """Return list of all descendant scope nodes recursively."""
        descendants: List[Scope] = []
        visited: Set[str] = set()
        stack: List[str] = [scope_id]

        while stack:
            curr_id = stack.pop()
            curr = self.scopes.get(curr_id)
            if not curr:
                continue

            for cid in curr.children_ids:
                if cid not in visited and cid in self.scopes:
                    visited.add(cid)
                    descendants.append(self.scopes[cid])
                    stack.append(cid)

        return descendants

    def get_scope_for_symbol(self, symbol_id: str) -> Optional[Scope]:
        """Return the `Scope` in which symbol_id is defined."""
        scope_id = self.symbol_to_scope_map.get(symbol_id)
        if not scope_id:
            return None
        return self.scopes.get(scope_id)

    def lookup_symbol(
        self,
        scope_id: str,
        symbol_name: str,
        symbol_table: SymbolTable,
    ) -> Optional[Symbol]:
        """
        Lexical symbol lookup starting at `scope_id` up to root scope.

        Parameters
        ----------
        scope_id:
            Target scope ID to search from.
        symbol_name:
            Identifier name (e.g. 'x', 'User').
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        Optional[Symbol]
            The closest visible symbol matching symbol_name, or None.
        """
        curr: Optional[Scope] = self.scopes.get(scope_id)
        visited: Set[str] = set()

        while curr:
            if curr.id in visited:
                break
            visited.add(curr.id)

            for sym_id in curr.defined_symbol_ids:
                sym = symbol_table.get_symbol(sym_id)
                if sym and sym.name == symbol_name:
                    return sym

            if not curr.parent_id:
                break
            curr = self.scopes.get(curr.parent_id)

        return None

    def get_visible_symbols(
        self,
        scope_id: str,
        symbol_table: SymbolTable,
    ) -> List[Symbol]:
        """
        Return list of all symbols visible from `scope_id`, handling shadowing.

        Parameters
        ----------
        scope_id:
            Target scope ID.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        List[Symbol]
        """
        seen_names: Set[str] = set()
        visible: List[Symbol] = []

        curr: Optional[Scope] = self.scopes.get(scope_id)
        visited: Set[str] = set()

        while curr:
            if curr.id in visited:
                break
            visited.add(curr.id)

            for sym_id in curr.defined_symbol_ids:
                sym = symbol_table.get_symbol(sym_id)
                if sym and sym.name not in seen_names:
                    seen_names.add(sym.name)
                    visible.append(sym)

            if not curr.parent_id:
                break
            curr = self.scopes.get(curr.parent_id)

        return visible

    def calculate_max_depth(self) -> int:
        """Calculate maximum scope hierarchy nesting depth."""
        if not self.root_scope_ids:
            return 0

        max_depth = 0

        def dfs(scope_id: str, depth: int) -> None:
            nonlocal max_depth
            if depth > max_depth:
                max_depth = depth
            scope = self.scopes.get(scope_id)
            if scope:
                for cid in scope.children_ids:
                    dfs(cid, depth + 1)

        for rid in self.root_scope_ids:
            dfs(rid, 1)

        return max_depth

    def __len__(self) -> int:
        return len(self.scopes)

    def __contains__(self, scope_id: str) -> bool:
        return scope_id in self.scopes
