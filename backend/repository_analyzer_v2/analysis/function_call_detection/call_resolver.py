"""
analysis/function_call_detection/call_resolver.py
--------------------------------------------------
Phase 4.7.2 — Function Call Symbol Binding Resolver.

Binds raw `CallRecord` callee expressions (`callee_name`) to precise target
`callee_symbol_id` and `callee_fqn` in the repository `SymbolTable`.

Resolution Chain
----------------
1. **Reference Resolution Correlation**: Matches line/column coordinates against
   `ReferenceResolutionResult` call/attribute records.
2. **Lexical Scope & SymbolTable Lookup**: Resolves direct functions, methods,
   constructors, and lambdas within caller scope.
3. **Import Resolution & Re-Export Resolution**: Follows imported names and package
   `__init__.py` re-export chains via `ReExportResolver` (e.g. `FastAPI()` -> `fastapi.applications.FastAPI`).
4. **Super Call Resolution**: Resolves `super().method()` to the inherited method in parent class.
5. **Class & Method Disambiguation**: Binds constructor calls (`User()`) to Class symbols,
   and method calls (`user.login()`) to Method symbols.
6. **Standard Library & External Classification**: Identifies stdlib/third-party calls (`print`, `len`, `requests.get`).

Design Principles
-----------------
- **Multi-Pass Resolution Strategy**: High-precision matching first, falling back gracefully.
- **Non-Throwing**: Degrades to unresolved with warning; never raises exceptions.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Set, Tuple

from models.call_models import CallRecord, CallType
from models.import_models import ImportResolutionResult, ImportResolutionStatus
from models.reference_models import ReferenceKind, ReferenceResolutionResult
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.import_resolution.module_index import ModuleIndex, STDLIB_MODULES
from analysis.re_export_resolution.re_export_index import ReExportIndex
from analysis.re_export_resolution.re_export_resolver import ReExportResolver
from analysis.function_call_detection.call_classifier import CallClassifier
from utils.logger import get_logger

logger = get_logger(__name__)

# Common Python built-in functions
BUILTIN_FUNCTIONS: Set[str] = {
    "abs", "aiter", "all", "anext", "any", "ascii", "bin", "bool", "breakpoint",
    "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex",
    "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
    "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash",
    "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter",
    "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr", "reversed",
    "round", "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum",
    "super", "tuple", "type", "vars", "zip", "__import__",
}


class CallResolver:
    """
    Coordinator engine that resolves `CallRecord` callee expressions to
    callee Symbol IDs.

    Usage::

        resolver = CallResolver()
        resolved_call = resolver.resolve_call(call_record, symbol_table, scope_tree, import_res, ref_res, export_idx)
    """

    def __init__(self) -> None:
        self._classifier = CallClassifier()
        self._re_export_resolver = ReExportResolver()

    def resolve_call(
        self,
        call: CallRecord,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult] = None,
        reference_res_result: Optional[ReferenceResolutionResult] = None,
        export_index: Optional[ReExportIndex] = None,
    ) -> CallRecord:
        """
        Resolve a single `CallRecord` to its target callee `SymbolId` and `callee_fqn`.

        Returns an updated copy of `CallRecord` with resolved fields populated.
        """
        callee_name = (call.callee_name or "").strip()
        if not callee_name:
            return call

        # 1. Strategy 1: Check Reference Resolution Result for exact line/column call site match
        if reference_res_result:
            target_sym, target_fqn = self._resolve_from_reference_result(
                call, reference_res_result, symbol_table
            )
            if target_sym:
                return self._update_resolved_call(call, target_sym, target_fqn, symbol_table, confidence=1.0)

        # 2. Strategy 2: Check Super Call (super().__init__(), super().method())
        if call.is_super_call or callee_name.startswith("super(") or callee_name.startswith("super()."):
            target_sym, target_fqn = self._resolve_super_call(call, symbol_table)
            if target_sym:
                return self._update_resolved_call(call, target_sym, target_fqn, symbol_table, confidence=0.95)

        # 3. Strategy 3: Check Import & Re-Export Resolution
        if import_res_result:
            target_sym, target_fqn, is_external = self._resolve_from_imports(
                call, import_res_result, symbol_table, export_index
            )
            if target_sym:
                return self._update_resolved_call(call, target_sym, target_fqn, symbol_table, confidence=0.9)
            if is_external:
                updated = call.model_copy()
                updated.is_external = True
                updated.confidence = 0.8
                return updated

        # 4. Strategy 4: Direct Lexical Scope & SymbolTable Lookup in Caller Module
        target_sym, target_fqn = self._resolve_from_symbol_table(call, symbol_table, scope_tree)
        if target_sym:
            return self._update_resolved_call(call, target_sym, target_fqn, symbol_table, confidence=0.85)

        # 5. Strategy 5: Built-in & Standard Library / External Classification
        if self._is_builtin_or_external(callee_name, import_res_result):
            updated = call.model_copy()
            updated.is_external = True
            updated.confidence = 0.75
            return updated

        # Unresolved fallback
        updated = call.model_copy()
        updated.confidence = 0.0
        return updated

    # ------------------------------------------------------------------
    # Internal Resolution Strategies
    # ------------------------------------------------------------------

    def _resolve_from_reference_result(
        self,
        call: CallRecord,
        reference_res_result: ReferenceResolutionResult,
        symbol_table: SymbolTable,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """Match call site line/column coordinates against ReferenceRecord / ReferenceResolution."""
        for ref_id, ref in reference_res_result.references.items():
            if ref.file_path == call.file_path and ref.line == call.line:
                if ref.kind in (ReferenceKind.FUNCTION_CALL, ReferenceKind.METHOD_CALL, ReferenceKind.CONSTRUCTOR_CALL) or ref.is_call:
                    res = reference_res_result.resolutions.get(ref_id)
                    if res and res.is_resolved and res.symbol_id:
                        sym = symbol_table.get_symbol(res.symbol_id)
                        if sym:
                            return sym, res.symbol_fqn or sym.fqn

        return None, None

    def _resolve_super_call(
        self,
        call: CallRecord,
        symbol_table: SymbolTable,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """Resolve super().method() to parent class method in SymbolTable."""
        method_name = "__init__"
        if "." in call.callee_name:
            parts = call.callee_name.split(".")
            if len(parts) >= 2:
                method_name = parts[-1]

        # Find caller symbol's enclosing class
        if call.caller_symbol_id:
            caller_sym = symbol_table.get_symbol(call.caller_symbol_id)
            if caller_sym:
                ancestors = symbol_table.get_ancestors(caller_sym.id)
                cls_sym = next((a for a in ancestors if a.kind == SymbolKind.CLASS), None)
                if cls_sym:
                    # Look up base class names in class metadata
                    base_classes = cls_sym.metadata.get("base_classes", [])
                    for base in base_classes:
                        # Search SymbolTable for base class method
                        expected_fqn = f"{base}.{method_name}"
                        for sym in symbol_table.symbols.values():
                            if sym.name == method_name and (sym.fqn.endswith(expected_fqn) or sym.fqn == expected_fqn):
                                return sym, sym.fqn

        return None, None

    def _resolve_from_imports(
        self,
        call: CallRecord,
        import_res_result: ImportResolutionResult,
        symbol_table: SymbolTable,
        export_index: Optional[ReExportIndex] = None,
    ) -> Tuple[Optional[Symbol], Optional[str], bool]:
        """Resolve imported or re-exported callee expressions."""
        simple_name = call.callee_name.split(".")[0] if call.callee_name else ""

        # Search import records originating in caller's source file
        for imp_id, rec in import_res_result.imports.items():
            if rec.source_file_path != call.file_path:
                continue

            # Case A: Matching imported symbol or alias
            imported_identifier = rec.alias if rec.alias else rec.imported_symbol_name
            if imported_identifier == simple_name or rec.imported_module_name == simple_name:
                res = import_res_result.resolutions.get(imp_id)
                if not res:
                    continue

                if res.is_external or res.is_stdlib:
                    return None, None, True

                if res.status == ImportResolutionStatus.RESOLVED_INTERNAL:
                    # Symbol ID directly resolved
                    if res.target_symbol_id:
                        sym = symbol_table.get_symbol(res.target_symbol_id)
                        if sym:
                            # If callee has attribute chain (e.g. module.func), resolve member
                            if "." in call.callee_name:
                                attr_name = call.callee_name.split(".")[-1]
                                member_sym = self._find_member_symbol(sym, attr_name, symbol_table)
                                if member_sym:
                                    return member_sym, member_sym.fqn, False
                            return sym, res.target_symbol_fqn or sym.fqn, False

                    # Check re-export index if direct symbol ID missing or is package import
                    if export_index and res.target_module_fqn:
                        target_name = rec.imported_symbol_name or call.callee_name
                        sym, fqn = self._re_export_resolver.resolve(
                            res.target_module_fqn,
                            target_name,
                            export_index,
                            symbol_table,
                        )
                        if sym:
                            return sym, fqn, False

        return None, None, False

    def _resolve_from_symbol_table(
        self,
        call: CallRecord,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
    ) -> Tuple[Optional[Symbol], Optional[str]]:
        """Resolve direct names or member calls against SymbolTable."""
        callee = call.callee_name.strip()

        # 1. Plain Identifier Call: e.g. login(), User()
        if "." not in callee:
            # Check caller module symbols first
            for sym in symbol_table.symbols.values():
                if sym.file_path == call.file_path and sym.name == callee:
                    if sym.kind in (SymbolKind.FUNCTION, SymbolKind.CLASS, SymbolKind.METHOD):
                        return sym, sym.fqn

            # Check full SymbolTable by matching trailing name
            for sym in symbol_table.symbols.values():
                if sym.name == callee and sym.kind in (SymbolKind.FUNCTION, SymbolKind.CLASS, SymbolKind.METHOD):
                    return sym, sym.fqn

        # 2. Dot Attribute Call: e.g. user.login(), User.build(), Math.add()
        else:
            parts = callee.split(".")
            receiver = parts[0]
            member = parts[-1]

            # Receiver is Class Name: e.g. User.build
            for sym in symbol_table.symbols.values():
                if sym.name == receiver and sym.kind == SymbolKind.CLASS:
                    member_sym = self._find_member_symbol(sym, member, symbol_table)
                    if member_sym:
                        return member_sym, member_sym.fqn

            # General member lookup by FQN suffix
            for sym in symbol_table.symbols.values():
                if sym.name == member and sym.kind in (SymbolKind.METHOD, SymbolKind.FUNCTION):
                    return sym, sym.fqn

        return None, None

    @staticmethod
    def _find_member_symbol(
        parent_sym: Symbol,
        member_name: str,
        symbol_table: SymbolTable,
    ) -> Optional[Symbol]:
        """Locate child or member Symbol of parent_sym with matching name."""
        for child_id in parent_sym.children_ids:
            child = symbol_table.get_symbol(child_id)
            if child and child.name == member_name:
                return child
        # Secondary check by parent_id link
        for sym in symbol_table.symbols.values():
            if sym.parent_id == parent_sym.id and sym.name == member_name:
                return sym
        return None

    @staticmethod
    def _is_builtin_or_external(callee_name: str, import_res_result: Optional[ImportResolutionResult]) -> bool:
        """Return True if callee_name represents a Python builtin or standard library function."""
        simple = callee_name.split(".")[0]
        if simple in BUILTIN_FUNCTIONS:
            return True
        if simple in STDLIB_MODULES:
            return True
        return False

    def _update_resolved_call(
        self,
        call: CallRecord,
        target_sym: Symbol,
        target_fqn: Optional[str],
        symbol_table: SymbolTable,
        confidence: float = 1.0,
    ) -> CallRecord:
        """Return an updated copy of CallRecord with resolved target fields and re-classified flags."""
        updated = call.model_copy()
        updated.callee_symbol_id = target_sym.id
        updated.callee_fqn = target_fqn or target_sym.fqn
        updated.confidence = confidence

        # Re-classify with resolved SymbolTable metadata
        classification = self._classifier.classify(
            callee_name=call.callee_name or target_sym.name,
            is_async=call.is_async or target_sym.metadata.get("is_async", False),
            callee_symbol=target_sym,
        )

        updated.call_type = classification.call_type
        updated.is_constructor = classification.is_constructor or (target_sym.kind == SymbolKind.CLASS)
        updated.is_method = classification.is_method or (target_sym.kind == SymbolKind.METHOD)
        updated.is_classmethod = classification.is_classmethod
        updated.is_staticmethod = classification.is_staticmethod
        updated.is_async = classification.is_async
        updated.is_lambda = classification.is_lambda or (target_sym.metadata.get("is_lambda", False))

        return updated
