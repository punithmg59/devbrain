"""
analysis/symbol_table/symbol_builder.py
---------------------------------------
Phase 4.4 — Symbol Table Builder.

Translates single-file semantic extraction results (`SemanticExtractionResult`) or
`ExtractedModule` entity trees into a canonical `SymbolTable`.

Design Principles
-----------------
- **Deterministic Symbol Generation**: Derives fully qualified names (FQNs) and
  SHA-256 seed symbol IDs deterministically.
- **Language-Independent Mapping**: Maps language constructs to abstract `SymbolKind`,
  `SymbolScope`, and `SymbolVisibility` entities.
- **Parent-Child Hierarchy Construction**: Automatically wires parent/child scope relationships.
- **Duplicate Detection & Diagnostics**: Captures duplicate symbol definitions without throwing exceptions.
- **Performance Telemetry**: Tracks build duration, symbol metrics, and memory footprint.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from models.semantic import (
    ExtractedClass,
    ExtractedDecorator,
    ExtractedFunction,
    ExtractedImport,
    ExtractedModule,
    ExtractedParameter,
    ExtractedVariable,
    MethodModifier,
    ParameterKind,
    SemanticExtractionResult,
    VariableScope,
)
from models.symbol import (
    Symbol,
    SymbolKind,
    SymbolLocation,
    SymbolMetrics,
    SymbolScope,
    SymbolVisibility,
    generate_symbol_id,
)
from analysis.symbol_table.symbol_table import SymbolTable
from utils.logger import get_logger

logger = get_logger(__name__)


def _infer_visibility(name: str) -> SymbolVisibility:
    """Infer symbol visibility from naming conventions (e.g. _protected, __private)."""
    if not name:
        return SymbolVisibility.PUBLIC
    if name.startswith("__") and not name.endswith("__"):
        return SymbolVisibility.PRIVATE
    if name.startswith("_") and not name.startswith("__"):
        return SymbolVisibility.PROTECTED
    return SymbolVisibility.PUBLIC


class SymbolTableBuilder:
    """
    Builder engine that constructs a `SymbolTable` from semantic extraction results.

    Usage::

        builder = SymbolTableBuilder(repository_id="my_repo")
        symbol_table = builder.build_from_results([result1, result2])
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._warnings: List[str] = []
        self._diagnostics: List[Dict[str, Any]] = []

    def build_from_result(
        self,
        extraction_result: SemanticExtractionResult,
    ) -> SymbolTable:
        """Convenience method to build a `SymbolTable` from a single `SemanticExtractionResult`."""
        return self.build_from_results([extraction_result])

    def build_from_results(
        self,
        extraction_results: List[SemanticExtractionResult],
    ) -> SymbolTable:
        """
        Build a unified `SymbolTable` from multiple file semantic extraction results.

        Parameters
        ----------
        extraction_results:
            List of `SemanticExtractionResult` outputs from language parser plugins.

        Returns
        -------
        SymbolTable
            Populated and frozen `SymbolTable`.
        """
        start_time = time.perf_counter()
        self._warnings.clear()
        self._diagnostics.clear()

        table = SymbolTable(repository_id=self.repository_id)
        duplicate_count = 0

        for result in extraction_results:
            dups = self._process_module(table, result.module, language=result.language)
            duplicate_count += dups

        # Collect metrics
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        memory_bytes = self._get_memory_bytes()

        symbols_by_kind: Dict[str, int] = {}
        symbols_by_file: Dict[str, int] = {}

        for sym in table.symbols.values():
            kind_str = sym.kind.value
            symbols_by_kind[kind_str] = symbols_by_kind.get(kind_str, 0) + 1
            symbols_by_file[sym.file_path] = symbols_by_file.get(sym.file_path, 0) + 1

        table.metrics = SymbolMetrics(
            total_symbols=len(table.symbols),
            symbols_by_kind=symbols_by_kind,
            symbols_by_file=symbols_by_file,
            duplicate_count=duplicate_count,
            build_duration_ms=round(duration_ms, 3),
            memory_bytes=memory_bytes,
        )

        table.freeze()
        return table

    def build_from_module(
        self,
        module: ExtractedModule,
        language: str = "python",
    ) -> SymbolTable:
        """Build a `SymbolTable` from a single `ExtractedModule` entity."""
        start_time = time.perf_counter()
        table = SymbolTable(repository_id=self.repository_id)

        duplicate_count = self._process_module(table, module, language=language)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        symbols_by_kind: Dict[str, int] = {}
        symbols_by_file: Dict[str, int] = {}

        for sym in table.symbols.values():
            kind_str = sym.kind.value
            symbols_by_kind[kind_str] = symbols_by_kind.get(kind_str, 0) + 1
            symbols_by_file[sym.file_path] = symbols_by_file.get(sym.file_path, 0) + 1

        table.metrics = SymbolMetrics(
            total_symbols=len(table.symbols),
            symbols_by_kind=symbols_by_kind,
            symbols_by_file=symbols_by_file,
            duplicate_count=duplicate_count,
            build_duration_ms=round(duration_ms, 3),
            memory_bytes=self._get_memory_bytes(),
        )

        table.freeze()
        return table

    # ------------------------------------------------------------------
    # Internal Module & Entity Converters
    # ------------------------------------------------------------------

    def _process_module(
        self,
        table: SymbolTable,
        module: ExtractedModule,
        language: str,
    ) -> int:
        """Process an `ExtractedModule` and add its entities to table."""
        duplicate_count = 0

        # Module Symbol
        mod_fqn = module.name
        mod_id = generate_symbol_id(self.repository_id, mod_fqn, SymbolKind.MODULE)

        mod_symbol = Symbol(
            id=mod_id,
            fqn=mod_fqn,
            name=module.name.split(".")[-1] if "." in module.name else module.name,
            kind=SymbolKind.MODULE,
            parent_id=None,
            file_path=module.file_path,
            scope=SymbolScope.MODULE,
            visibility=SymbolVisibility.PUBLIC,
            language=language,
            repository_id=self.repository_id,
            metadata={"docstring": module.docstring} if module.docstring else {},
        )

        if mod_id in table.symbols:
            duplicate_count += 1
            self._record_duplicate(mod_id, mod_fqn)
        else:
            table.add_symbol(mod_symbol)

        # 1. Imports
        for imp in module.imports:
            d = self._process_import(table, imp, parent_symbol=mod_symbol, language=language)
            duplicate_count += d

        # 2. Global Variables & Constants
        for var in module.global_variables:
            d = self._process_variable(table, var, parent_symbol=mod_symbol, language=language)
            duplicate_count += d

        for const in module.constants:
            d = self._process_variable(table, const, parent_symbol=mod_symbol, language=language)
            duplicate_count += d

        # 3. Classes
        for cls in module.classes:
            d = self._process_class(table, cls, parent_symbol=mod_symbol, language=language)
            duplicate_count += d

        # 4. Top-level Functions
        for fn in module.functions:
            d = self._process_function(table, fn, parent_symbol=mod_symbol, language=language)
            duplicate_count += d

        return duplicate_count

    def _process_import(
        self,
        table: SymbolTable,
        imp: ExtractedImport,
        parent_symbol: Symbol,
        language: str,
    ) -> int:
        """Process an `ExtractedImport` entity."""
        dups = 0
        imp_name = imp.module or (imp.imported_names[0] if imp.imported_names else "import")
        fqn = f"{parent_symbol.fqn}.import:{imp_name}"
        sym_id = generate_symbol_id(self.repository_id, fqn, SymbolKind.IMPORT)

        loc = SymbolLocation(file_path=parent_symbol.file_path, range=imp.range) if imp.range else None

        sym = Symbol(
            id=sym_id,
            fqn=fqn,
            name=imp_name,
            kind=SymbolKind.IMPORT,
            parent_id=parent_symbol.id,
            file_path=parent_symbol.file_path,
            location=loc,
            scope=SymbolScope.MODULE,
            visibility=SymbolVisibility.PUBLIC,
            language=language,
            repository_id=self.repository_id,
            metadata={
                "module": imp.module,
                "imported_names": imp.imported_names,
                "aliases": imp.aliases,
                "is_relative": imp.is_relative,
                "relative_level": imp.relative_level,
            },
        )

        if sym_id in table.symbols:
            dups += 1
            self._record_duplicate(sym_id, fqn)
        else:
            table.add_symbol(sym)

        return dups

    def _process_class(
        self,
        table: SymbolTable,
        cls: ExtractedClass,
        parent_symbol: Symbol,
        language: str,
    ) -> int:
        """Process an `ExtractedClass` entity."""
        dups = 0
        fqn = f"{parent_symbol.fqn}.{cls.name}"
        sym_id = generate_symbol_id(self.repository_id, fqn, SymbolKind.CLASS)

        loc = SymbolLocation(file_path=parent_symbol.file_path, range=cls.range) if cls.range else None
        vis = _infer_visibility(cls.name)

        sym = Symbol(
            id=sym_id,
            fqn=fqn,
            name=cls.name,
            kind=SymbolKind.CLASS,
            parent_id=parent_symbol.id,
            file_path=parent_symbol.file_path,
            location=loc,
            scope=SymbolScope.CLASS if parent_symbol.kind == SymbolKind.CLASS else SymbolScope.MODULE,
            visibility=vis,
            language=language,
            repository_id=self.repository_id,
            metadata={
                "docstring": cls.docstring,
                "base_classes": cls.base_classes,
                "nesting_level": cls.nesting_level,
                "parent_class": cls.parent_class,
            },
        )

        if sym_id in table.symbols:
            dups += 1
            self._record_duplicate(sym_id, fqn)
        else:
            table.add_symbol(sym)

        # Class Decorators
        for dec in cls.decorators:
            dups += self._process_decorator(table, dec, parent_symbol=sym, language=language)

        # Class Attributes
        for attr in cls.class_attributes:
            dups += self._process_variable(table, attr, parent_symbol=sym, language=language)

        # Methods
        for method in cls.methods:
            dups += self._process_function(table, method, parent_symbol=sym, language=language)

        return dups

    def _process_function(
        self,
        table: SymbolTable,
        fn: ExtractedFunction,
        parent_symbol: Symbol,
        language: str,
    ) -> int:
        """Process an `ExtractedFunction` entity."""
        dups = 0
        kind = SymbolKind.METHOD if parent_symbol.kind == SymbolKind.CLASS else SymbolKind.FUNCTION
        fqn = f"{parent_symbol.fqn}.{fn.name}"
        sym_id = generate_symbol_id(self.repository_id, fqn, kind)

        loc = SymbolLocation(file_path=parent_symbol.file_path, range=fn.range) if fn.range else None
        vis = _infer_visibility(fn.name)

        scope = SymbolScope.CLASS if parent_symbol.kind == SymbolKind.CLASS else (
            SymbolScope.LOCAL if parent_symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) else SymbolScope.MODULE
        )

        sym = Symbol(
            id=sym_id,
            fqn=fqn,
            name=fn.name,
            kind=kind,
            parent_id=parent_symbol.id,
            file_path=parent_symbol.file_path,
            location=loc,
            scope=scope,
            visibility=vis,
            language=language,
            repository_id=self.repository_id,
            metadata={
                "docstring": fn.docstring,
                "is_async": fn.is_async,
                "is_generator": fn.is_generator,
                "return_annotation": fn.return_annotation,
                "nesting_level": fn.nesting_level,
                "enclosing_class": fn.enclosing_class,
                "enclosing_function": fn.enclosing_function,
                "method_modifiers": [m.value for m in fn.method_modifiers],
            },
        )

        if sym_id in table.symbols:
            dups += 1
            self._record_duplicate(sym_id, fqn)
        else:
            table.add_symbol(sym)

        # Decorators
        for dec in fn.decorators:
            dups += self._process_decorator(table, dec, parent_symbol=sym, language=language)

        # Parameters
        for param in fn.parameters:
            dups += self._process_parameter(table, param, parent_symbol=sym, language=language)

        # Local Variables
        for var in fn.local_variables:
            dups += self._process_variable(table, var, parent_symbol=sym, language=language)

        return dups

    def _process_parameter(
        self,
        table: SymbolTable,
        param: ExtractedParameter,
        parent_symbol: Symbol,
        language: str,
    ) -> int:
        """Process an `ExtractedParameter` entity."""
        dups = 0
        fqn = f"{parent_symbol.fqn}.{param.name}"
        sym_id = generate_symbol_id(self.repository_id, fqn, SymbolKind.PARAMETER)

        sym = Symbol(
            id=sym_id,
            fqn=fqn,
            name=param.name,
            kind=SymbolKind.PARAMETER,
            parent_id=parent_symbol.id,
            file_path=parent_symbol.file_path,
            location=parent_symbol.location,
            scope=SymbolScope.LOCAL,
            visibility=SymbolVisibility.PUBLIC,
            language=language,
            repository_id=self.repository_id,
            metadata={
                "annotation": param.annotation,
                "has_default": param.has_default,
                "default_value": param.default_value,
                "kind": param.kind.value,
            },
        )

        if sym_id in table.symbols:
            dups += 1
            self._record_duplicate(sym_id, fqn)
        else:
            table.add_symbol(sym)

        return dups

    def _process_variable(
        self,
        table: SymbolTable,
        var: ExtractedVariable,
        parent_symbol: Symbol,
        language: str,
    ) -> int:
        """Process an `ExtractedVariable` entity."""
        dups = 0
        kind = SymbolKind.CONSTANT if var.is_constant else (
            SymbolKind.PROPERTY if parent_symbol.kind == SymbolKind.CLASS else SymbolKind.VARIABLE
        )

        fqn = f"{parent_symbol.fqn}.{var.name}"
        sym_id = generate_symbol_id(self.repository_id, fqn, kind)

        loc = SymbolLocation(file_path=parent_symbol.file_path, range=var.range) if var.range else None
        vis = _infer_visibility(var.name)

        scope = SymbolScope.CLASS if parent_symbol.kind == SymbolKind.CLASS else (
            SymbolScope.LOCAL if parent_symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) else SymbolScope.MODULE
        )

        sym = Symbol(
            id=sym_id,
            fqn=fqn,
            name=var.name,
            kind=kind,
            parent_id=parent_symbol.id,
            file_path=parent_symbol.file_path,
            location=loc,
            scope=scope,
            visibility=vis,
            language=language,
            repository_id=self.repository_id,
            metadata={
                "annotation": var.annotation,
                "inferred_expression_kind": var.inferred_expression_kind,
                "is_constant": var.is_constant,
                "value_snippet": var.value_snippet,
            },
        )

        if sym_id in table.symbols:
            dups += 1
            self._record_duplicate(sym_id, fqn)
        else:
            table.add_symbol(sym)

        return dups

    def _process_decorator(
        self,
        table: SymbolTable,
        dec: ExtractedDecorator,
        parent_symbol: Symbol,
        language: str,
    ) -> int:
        """Process an `ExtractedDecorator` entity."""
        dups = 0
        fqn = f"{parent_symbol.fqn}.decorator:{dec.name}"
        sym_id = generate_symbol_id(self.repository_id, fqn, SymbolKind.DECORATOR)

        loc = SymbolLocation(file_path=parent_symbol.file_path, range=dec.range) if dec.range else None

        sym = Symbol(
            id=sym_id,
            fqn=fqn,
            name=dec.name,
            kind=SymbolKind.DECORATOR,
            parent_id=parent_symbol.id,
            file_path=parent_symbol.file_path,
            location=loc,
            scope=parent_symbol.scope,
            visibility=SymbolVisibility.PUBLIC,
            language=language,
            repository_id=self.repository_id,
            metadata={
                "expression": dec.expression,
                "arguments": dec.arguments,
            },
        )

        if sym_id in table.symbols:
            dups += 1
            self._record_duplicate(sym_id, fqn)
        else:
            table.add_symbol(sym)

        return dups

    def _record_duplicate(self, sym_id: str, fqn: str) -> None:
        """Record diagnostic record for duplicate symbol."""
        diag = {
            "severity": "warning",
            "code": "DUPLICATE_SYMBOL",
            "message": f"Duplicate symbol declaration detected: '{fqn}'",
            "symbol_id": sym_id,
            "fqn": fqn,
        }
        self._diagnostics.append(diag)
        logger.warning(f"[SymbolTableBuilder] {diag['message']}")

    @staticmethod
    def _get_memory_bytes() -> int:
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            return 0
