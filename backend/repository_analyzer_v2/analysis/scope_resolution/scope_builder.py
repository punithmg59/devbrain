"""
analysis/scope_resolution/scope_builder.py
-----------------------------------------
Phase 4.5 — Scope Builder Engine.

Transforms `SemanticExtractionResult` / `ExtractedModule` and a repository `SymbolTable`
into a canonical `ScopeTree`.

Design Principles
-----------------
- **Lexical Scope Construction**: Builds explicit `Scope` nodes for modules, classes,
  functions, methods, nested functions, lambdas, and comprehensions.
- **ScopeStack Integration**: Manages scope nesting during walk with `ScopeStack`.
- **Visible Symbol Calculation**: Populates `visible_symbol_ids` for every scope node.
- **Name Shadowing Detection**: Detects when inner symbols shadow outer symbols and records
  `ShadowingRelationship` objects.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Set

from models.scope import (
    Scope,
    ScopeKind,
    ScopeLocation,
    ScopeMetrics,
    ShadowingRelationship,
)
from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedModule,
    ExtractedVariable,
    SemanticExtractionResult,
)
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_stack import ScopeStack
from analysis.scope_resolution.scope_tree import ScopeTree
from utils.logger import get_logger

logger = get_logger(__name__)


class ScopeBuilder:
    """
    Engine that constructs a `ScopeTree` from semantic models and a `SymbolTable`.

    Usage::

        builder = ScopeBuilder(repository_id="repo1")
        tree, shadowing = builder.build_from_module(module, symbol_table)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._shadowing_records: List[ShadowingRelationship] = []

    def build_from_result(
        self,
        result: SemanticExtractionResult,
        symbol_table: SymbolTable,
    ) -> Tuple[ScopeTree, List[ShadowingRelationship]]:
        """Build `ScopeTree` from a single `SemanticExtractionResult`."""
        return self.build_from_module(result.module, symbol_table)

    def build_from_module(
        self,
        module: ExtractedModule,
        symbol_table: SymbolTable,
    ) -> Tuple[ScopeTree, List[ShadowingRelationship]]:
        """
        Build a `ScopeTree` from an `ExtractedModule` and repository `SymbolTable`.

        Parameters
        ----------
        module:
            Extracted module entity.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        Tuple[ScopeTree, List[ShadowingRelationship]]
            Constructed ScopeTree and list of detected shadowing records.
        """
        start_time = time.perf_counter()
        self._shadowing_records.clear()

        tree = ScopeTree(repository_id=self.repository_id)
        stack = ScopeStack()

        # 1. Module Scope
        mod_symbols = [
            s for s in symbol_table.symbols.values()
            if s.file_path == module.file_path and s.kind == SymbolKind.MODULE
        ]
        mod_sym = mod_symbols[0] if mod_symbols else None

        mod_scope = Scope(
            name=f"module:{module.name}",
            kind=ScopeKind.MODULE,
            parent_id=None,
            file_path=module.file_path,
        )

        # Collect symbols defined at top-level module scope
        for sym in symbol_table.symbols.values():
            if sym.file_path == module.file_path and sym.parent_id == (mod_sym.id if mod_sym else None):
                mod_scope.defined_symbol_ids.append(sym.id)

        tree.add_scope(mod_scope)
        stack.push_scope(mod_scope)

        # Process Module Members (Classes, Functions)
        for cls in module.classes:
            self._process_class(tree, stack, cls, module.file_path, symbol_table)

        for fn in module.functions:
            self._process_function(tree, stack, fn, module.file_path, symbol_table)

        # Populate visible symbols for module scope
        mod_scope.visible_symbol_ids = [
            s.id for s in stack.get_all_visible_symbols(symbol_table)
        ]

        stack.pop_scope()

        # Collect Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        scopes_by_kind: Dict[str, int] = {}
        for sc in tree.scopes.values():
            k = sc.kind.value
            scopes_by_kind[k] = scopes_by_kind.get(k, 0) + 1

        tree.metrics = ScopeMetrics(
            total_scopes=len(tree.scopes),
            scopes_by_kind=scopes_by_kind,
            max_nesting_depth=tree.calculate_max_depth(),
            total_symbols_defined=sum(len(s.defined_symbol_ids) for s in tree.scopes.values()),
            shadowing_count=len(self._shadowing_records),
            build_duration_ms=round(duration_ms, 3),
            memory_bytes=self._get_memory_bytes(),
        )

        return tree, list(self._shadowing_records)

    # ------------------------------------------------------------------
    # Scope Converters
    # ------------------------------------------------------------------

    def _process_class(
        self,
        tree: ScopeTree,
        stack: ScopeStack,
        cls: ExtractedClass,
        file_path: str,
        symbol_table: SymbolTable,
    ) -> None:
        """Process an `ExtractedClass` entity into a CLASS Scope."""
        parent_scope = stack.current_scope()

        cls_loc = ScopeLocation(file_path=file_path, range=cls.range) if cls.range else None
        cls_scope = Scope(
            name=f"class:{cls.name}",
            kind=ScopeKind.CLASS,
            parent_id=parent_scope.id if parent_scope else None,
            file_path=file_path,
            location=cls_loc,
            metadata={"nesting_level": cls.nesting_level, "base_classes": cls.base_classes},
        )

        tree.add_scope(cls_scope)
        stack.push_scope(cls_scope)

        # Find Symbol for class in symbol_table
        cls_syms = [
            s for s in symbol_table.symbols.values()
            if s.file_path == file_path and s.name == cls.name and s.kind == SymbolKind.CLASS
        ]
        cls_sym = cls_syms[0] if cls_syms else None

        if cls_sym:
            for sym in symbol_table.symbols.values():
                if sym.file_path == file_path and sym.parent_id == cls_sym.id:
                    cls_scope.defined_symbol_ids.append(sym.id)
                    # Check Shadowing against outer scopes
                    sh = stack.check_shadowing(sym.name, sym.id, symbol_table)
                    if sh:
                        cls_scope.shadowed_symbols.append(sh)
                        self._shadowing_records.append(sh)

        # Process methods inside class
        for method in cls.methods:
            self._process_function(tree, stack, method, file_path, symbol_table)

        # Calculate visible symbols inside class scope
        cls_scope.visible_symbol_ids = [
            s.id for s in stack.get_all_visible_symbols(symbol_table)
        ]

        stack.pop_scope()

    def _process_function(
        self,
        tree: ScopeTree,
        stack: ScopeStack,
        fn: ExtractedFunction,
        file_path: str,
        symbol_table: SymbolTable,
    ) -> None:
        """Process an `ExtractedFunction` entity into a FUNCTION Scope."""
        parent_scope = stack.current_scope()

        fn_kind = ScopeKind.LAMBDA if fn.name == "<lambda>" else ScopeKind.FUNCTION
        fn_loc = ScopeLocation(file_path=file_path, range=fn.range) if fn.range else None

        fn_scope = Scope(
            name=f"function:{fn.name}",
            kind=fn_kind,
            parent_id=parent_scope.id if parent_scope else None,
            file_path=file_path,
            location=fn_loc,
            metadata={
                "is_async": fn.is_async,
                "is_generator": fn.is_generator,
                "nesting_level": fn.nesting_level,
                "enclosing_class": fn.enclosing_class,
                "enclosing_function": fn.enclosing_function,
            },
        )

        tree.add_scope(fn_scope)
        stack.push_scope(fn_scope)

        # Find Function symbol in symbol_table
        fn_syms = [
            s for s in symbol_table.symbols.values()
            if s.file_path == file_path and s.name == fn.name and s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
        ]
        fn_sym = fn_syms[0] if fn_syms else None

        if fn_sym:
            # Function parameters & local variables belong to function scope
            for sym in symbol_table.symbols.values():
                if sym.file_path == file_path and sym.parent_id == fn_sym.id:
                    fn_scope.defined_symbol_ids.append(sym.id)
                    # Check Shadowing against outer scopes
                    sh = stack.check_shadowing(sym.name, sym.id, symbol_table)
                    if sh:
                        fn_scope.shadowed_symbols.append(sh)
                        self._shadowing_records.append(sh)

        # Calculate visible symbols inside function scope
        fn_scope.visible_symbol_ids = [
            s.id for s in stack.get_all_visible_symbols(symbol_table)
        ]

        stack.pop_scope()

    @staticmethod
    def _get_memory_bytes() -> int:
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            return 0
