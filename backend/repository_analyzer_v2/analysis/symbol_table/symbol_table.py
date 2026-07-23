"""
analysis/symbol_table/symbol_table.py
--------------------------------------
Phase 4.4 — Symbol Table Core Representation.

Provides the canonical, thread-safe, immutable `SymbolTable` data container for
a repository. Manages symbol entities, parent-child scope linkage navigation,
and table immutability freezing.

Design Principles
-----------------
- **Language-Agnostic**: Pure container of `Symbol` objects.
- **Parent-Child Hierarchy Navigation**: Fast traversal of parent, children, ancestors,
  and descendants.
- **Immutability Enforcement**: Thread-safe once frozen via `freeze()`.
- **Zero Heavy Dependencies**: Pure Python logic with Pydantic V2 models.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from models.symbol import Symbol, SymbolMetrics


class SymbolTable(BaseModel):
    """
    Canonical repository symbol table container.

    Holds all declared symbols for a repository indexed by their unique symbol ID.
    Supports parent-child hierarchy queries and immutability locking.
    """

    table_id: str = Field(
        default_factory=lambda: f"symtab-{uuid.uuid4().hex[:12]}",
        description="Globally unique symbol table instance ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    symbols: Dict[str, Symbol] = Field(
        default_factory=dict,
        description="Map of symbol_id -> Symbol object",
    )
    root_symbol_ids: List[str] = Field(
        default_factory=list,
        description="IDs of root symbols (top-level modules/packages)",
    )
    metrics: SymbolMetrics = Field(
        default_factory=SymbolMetrics,
        description="Build metrics and statistics telemetry",
    )
    is_frozen: bool = Field(
        default=False,
        description="True if table is frozen (immutable) after construction",
    )

    def add_symbol(self, symbol: Symbol) -> None:
        """
        Add a symbol to the table.

        Parameters
        ----------
        symbol:
            The `Symbol` object to add.

        Raises
        ------
        RuntimeError
            If the table is frozen.
        """
        if self.is_frozen:
            raise RuntimeError("Cannot modify a frozen SymbolTable")

        self.symbols[symbol.id] = symbol

        if symbol.parent_id is None:
            if symbol.id not in self.root_symbol_ids:
                self.root_symbol_ids.append(symbol.id)
        else:
            # Wire child ID into parent if parent exists in table
            parent = self.symbols.get(symbol.parent_id)
            if parent and symbol.id not in parent.children_ids:
                parent.children_ids.append(symbol.id)

    def freeze(self) -> None:
        """Lock the symbol table to prevent further mutations."""
        self.is_frozen = True

    def get_symbol(self, symbol_id: str) -> Optional[Symbol]:
        """Return `Symbol` by its unique ID, or None if not found."""
        return self.symbols.get(symbol_id)

    def get_children(self, symbol_id: str) -> List[Symbol]:
        """
        Return list of direct child `Symbol` objects for symbol_id.

        Parameters
        ----------
        symbol_id:
            Target symbol ID.

        Returns
        -------
        List[Symbol]
        """
        symbol = self.symbols.get(symbol_id)
        if not symbol:
            return []
        return [
            self.symbols[cid]
            for cid in symbol.children_ids
            if cid in self.symbols
        ]

    def get_parent(self, symbol_id: str) -> Optional[Symbol]:
        """
        Return the direct parent `Symbol` for symbol_id, or None.

        Parameters
        ----------
        symbol_id:
            Target symbol ID.

        Returns
        -------
        Optional[Symbol]
        """
        symbol = self.symbols.get(symbol_id)
        if not symbol or not symbol.parent_id:
            return None
        return self.symbols.get(symbol.parent_id)

    def get_ancestors(self, symbol_id: str) -> List[Symbol]:
        """
        Return ordered list of ancestor symbols from immediate parent up to root.

        Parameters
        ----------
        symbol_id:
            Target symbol ID.

        Returns
        -------
        List[Symbol]
        """
        ancestors: List[Symbol] = []
        visited: Set[str] = set()
        curr_id = symbol_id

        while curr_id:
            symbol = self.symbols.get(curr_id)
            if not symbol or not symbol.parent_id:
                break
            pid = symbol.parent_id
            if pid in visited:
                break  # Prevent infinite loop in malformed circular parent structures
            visited.add(pid)
            parent = self.symbols.get(pid)
            if parent:
                ancestors.append(parent)
                curr_id = pid
            else:
                break

        return ancestors

    def get_descendants(self, symbol_id: str) -> List[Symbol]:
        """
        Return list of all descendant symbols recursively.

        Parameters
        ----------
        symbol_id:
            Target symbol ID.

        Returns
        -------
        List[Symbol]
        """
        descendants: List[Symbol] = []
        visited: Set[str] = set()
        stack: List[str] = [symbol_id]

        while stack:
            curr_id = stack.pop()
            curr = self.symbols.get(curr_id)
            if not curr:
                continue

            for cid in curr.children_ids:
                if cid not in visited and cid in self.symbols:
                    visited.add(cid)
                    descendants.append(self.symbols[cid])
                    stack.append(cid)

        return descendants

    def __len__(self) -> int:
        return len(self.symbols)

    def __contains__(self, symbol_id: str) -> bool:
        return symbol_id in self.symbols
