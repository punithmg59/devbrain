"""
analysis/scope_resolution/scope_stack.py
-----------------------------------------
Phase 4.5 — Scope Stack Tracker.

Maintains the active stack of nested lexical scopes during tree traversal.
Provides lexical lookup, symbol shadowing detection, and scope visibility calculations.

Design Principles
-----------------
- **Lexical Stack Semantics**: Operates strictly as a LIFO stack (`push_scope`, `pop_scope`).
- **Inner-to-Outer Resolution**: Searches from current scope up to root scope.
- **Shadowing Awareness**: Detects when an inner declaration shadows an outer declaration.
- **State Safety**: Prevents stack corruption or state leakage across traversal phases.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from models.scope import Scope, ShadowingRelationship
from models.symbol import Symbol
from analysis.symbol_table.symbol_table import SymbolTable


class ScopeStack:
    """
    Active lexical scope stack tracker used during scope construction and resolution.
    """

    def __init__(self) -> None:
        self._stack: List[Scope] = []

    def push_scope(self, scope: Scope) -> None:
        """Push a scope onto the top of the stack."""
        self._stack.append(scope)

    def pop_scope(self) -> Scope:
        """
        Pop and return the top scope from the stack.

        Raises
        ------
        RuntimeError
            If the stack is empty.
        """
        if not self._stack:
            raise RuntimeError("Cannot pop from an empty ScopeStack")
        return self._stack.pop()

    def current_scope(self) -> Optional[Scope]:
        """Return the current top scope without removing it."""
        return self._stack[-1] if self._stack else None

    @property
    def depth(self) -> int:
        """Return the current nesting depth of the stack."""
        return len(self._stack)

    def is_empty(self) -> bool:
        """Return True if the stack is empty."""
        return len(self._stack) == 0

    def resolve_visible_symbol(
        self,
        symbol_name: str,
        symbol_table: SymbolTable,
    ) -> Optional[Symbol]:
        """
        Search for a visible symbol by name from current scope down to root scope.

        Parameters
        ----------
        symbol_name:
            Target identifier name (e.g. 'x', 'User').
        symbol_table:
            The repository `SymbolTable` containing symbol objects.

        Returns
        -------
        Optional[Symbol]
            The closest visible `Symbol`, or None if not in scope.
        """
        # Walk stack from innermost (top) to outermost (bottom)
        for scope in reversed(self._stack):
            for sym_id in scope.defined_symbol_ids:
                sym = symbol_table.get_symbol(sym_id)
                if sym and sym.name == symbol_name:
                    return sym
        return None

    def get_all_visible_symbols(
        self,
        symbol_table: SymbolTable,
    ) -> List[Symbol]:
        """
        Collect all symbols visible from the current scope, accounting for shadowing.

        Returns
        -------
        List[Symbol]
            List of unique visible `Symbol` instances.
        """
        seen_names: Set[str] = set()
        visible: List[Symbol] = []

        # Walk stack from innermost to outermost
        for scope in reversed(self._stack):
            for sym_id in scope.defined_symbol_ids:
                sym = symbol_table.get_symbol(sym_id)
                if sym and sym.name not in seen_names:
                    seen_names.add(sym.name)
                    visible.append(sym)

        return visible

    def check_shadowing(
        self,
        symbol_name: str,
        symbol_id: str,
        symbol_table: SymbolTable,
    ) -> Optional[ShadowingRelationship]:
        """
        Check if `symbol_name` in current scope shadows an outer symbol on the stack.

        Parameters
        ----------
        symbol_name:
            Identifier name of the inner symbol.
        symbol_id:
            Symbol ID of the inner symbol.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        Optional[ShadowingRelationship]
            Shadowing record if an outer symbol was shadowed, or None.
        """
        if len(self._stack) <= 1:
            return None

        inner_scope = self._stack[-1]

        # Search outer scopes (excluding current innermost scope at index -1)
        for outer_scope in reversed(self._stack[:-1]):
            for sym_id in outer_scope.defined_symbol_ids:
                sym = symbol_table.get_symbol(sym_id)
                if sym and sym.name == symbol_name and sym.id != symbol_id:
                    return ShadowingRelationship(
                        name=symbol_name,
                        shadowing_symbol_id=symbol_id,
                        shadowed_symbol_id=sym.id,
                        inner_scope_id=inner_scope.id,
                        outer_scope_id=outer_scope.id,
                    )
        return None
