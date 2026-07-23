"""
analysis/reference_resolution/reference_builder.py
---------------------------------------------
Phase 4.7 — Reference Builder Engine.

Transforms `SemanticExtractionResult` / `ExtractedModule`, `SymbolTable`, `ScopeTree`, and
`ImportResolutionResult` into a list of canonical `ReferenceRecord` and `ReferenceResolution` objects.

Design Principles
-----------------
- **Deterministic Symbol Binding**: Resolves usage identifiers to `SymbolId` using Lexical Scope, Imports, and SymbolTable maps.
- **Access Kind Classification**: Categorizes Definition, Read, Write, Read+Write, Call, and Attribute Access.
"""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Tuple

from models.import_models import ImportResolutionResult, ImportResolutionStatus
from models.reference_models import (
    ReferenceKind,
    ReferenceRecord,
    ReferenceResolution,
)
from analysis.scope_resolution.scope_tree import ScopeTree
from models.semantic import (
    ExtractedClass,
    ExtractedFunction,
    ExtractedModule,
    ExtractedVariable,
    SemanticExtractionResult,
)
from models.symbol import Symbol, SymbolKind
from analysis.symbol_table.symbol_table import SymbolTable
from utils.logger import get_logger

logger = get_logger(__name__)


class ReferenceBuilder:
    """
    Engine that constructs identifier references and resolves symbol bindings.

    Usage::

        builder = ReferenceBuilder(repository_id="repo1")
        records, resolutions = builder.build_from_module(module, symbol_table, scope_tree, import_res)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id

    def build_from_module(
        self,
        module: ExtractedModule,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult] = None,
    ) -> Tuple[List[ReferenceRecord], List[ReferenceResolution]]:
        """
        Build reference records and resolutions for an `ExtractedModule`.

        Parameters
        ----------
        module:
            Source module entity.
        symbol_table:
            Repository `SymbolTable`.
        scope_tree:
            Lexical `ScopeTree`.
        import_res_result:
            Optional `ImportResolutionResult`.

        Returns
        -------
        Tuple[List[ReferenceRecord], List[ReferenceResolution]]
        """
        records: List[ReferenceRecord] = []
        resolutions: List[ReferenceResolution] = []

        # Find module scope ID
        mod_scope = next(
            (s for s in scope_tree.scopes.values() if s.kind == "module" and s.file_path == module.file_path),
            None,
        )
        mod_scope_id = mod_scope.id if mod_scope else "root"

        # 1. Process Module Definitions & Constants
        for sym in symbol_table.symbols.values():
            if sym.file_path == module.file_path and sym.kind == SymbolKind.MODULE:
                rec, res = self._create_reference(
                    symbol_name=sym.name,
                    kind=ReferenceKind.VARIABLE_DEFINITION,
                    scope_id=mod_scope_id,
                    file_path=module.file_path,
                    target_symbol=sym,
                    line=sym.location.range.start.line if sym.location and sym.location.range else 1,
                    column=sym.location.range.start.column if sym.location and sym.location.range else 0,
                    end_line=sym.location.range.end.line if sym.location and sym.location.range else 1,
                    end_column=sym.location.range.end.column if sym.location and sym.location.range else 10,
                    is_definition=True,
                )
                records.append(rec)
                resolutions.append(res)

        # 2. Process Global Variables & Constants
        for var in module.global_variables + module.constants:
            sym = self._resolve_name(var.name, mod_scope_id, symbol_table, scope_tree, import_res_result)
            rng = var.range
            rec, res = self._create_reference(
                symbol_name=var.name,
                kind=ReferenceKind.VARIABLE_DEFINITION,
                scope_id=mod_scope_id,
                file_path=module.file_path,
                target_symbol=sym,
                line=rng.start.line if rng else 1,
                column=rng.start.column if rng else 0,
                end_line=rng.end.line if rng else 1,
                end_column=rng.end.column if rng else 10,
                is_definition=True,
                is_write=True,
            )
            records.append(rec)
            resolutions.append(res)

        # 3. Process Classes
        for cls in module.classes:
            cls_records, cls_resolutions = self._process_class(
                cls, module.file_path, symbol_table, scope_tree, import_res_result, mod_scope_id
            )
            records.extend(cls_records)
            resolutions.extend(cls_resolutions)

        # 4. Process Top-level Functions
        for fn in module.functions:
            fn_records, fn_resolutions = self._process_function(
                fn, module.file_path, symbol_table, scope_tree, import_res_result, mod_scope_id
            )
            records.extend(fn_records)
            resolutions.extend(fn_resolutions)

        return records, resolutions

    # ------------------------------------------------------------------
    # Internal Traversal Helpers
    # ------------------------------------------------------------------

    def _process_class(
        self,
        cls: ExtractedClass,
        file_path: str,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult],
        parent_scope_id: str,
    ) -> Tuple[List[ReferenceRecord], List[ReferenceResolution]]:
        records: List[ReferenceRecord] = []
        resolutions: List[ReferenceResolution] = []

        cls_scope = next(
            (s for s in scope_tree.scopes.values() if s.kind == "class" and s.name == f"class:{cls.name}" and s.file_path == file_path),
            None,
        )
        cls_scope_id = cls_scope.id if cls_scope else parent_scope_id

        # Class Definition Site Reference
        cls_sym = self._resolve_name(cls.name, parent_scope_id, symbol_table, scope_tree, import_res_result)
        rng = cls.range
        rec, res = self._create_reference(
            symbol_name=cls.name,
            kind=ReferenceKind.CLASS_DEFINITION,
            scope_id=parent_scope_id,
            file_path=file_path,
            target_symbol=cls_sym,
            line=rng.start.line if rng else 1,
            column=rng.start.column if rng else 0,
            end_line=rng.end.line if rng else 1,
            end_column=rng.end.column if rng else 10,
            is_definition=True,
        )
        records.append(rec)
        resolutions.append(res)

        # Base Class References
        for base_name in cls.base_classes:
            base_sym = self._resolve_name(base_name, parent_scope_id, symbol_table, scope_tree, import_res_result)
            rec_b, res_b = self._create_reference(
                symbol_name=base_name,
                kind=ReferenceKind.TYPE_ANNOTATION,
                scope_id=parent_scope_id,
                file_path=file_path,
                target_symbol=base_sym,
                line=rng.start.line if rng else 1,
                column=rng.start.column if rng else 0,
                end_line=rng.end.line if rng else 1,
                end_column=rng.end.column if rng else 10,
                is_read=True,
            )
            records.append(rec_b)
            resolutions.append(res_b)

        # Process Class Attributes
        for attr in cls.class_attributes:
            attr_sym = self._resolve_name(attr.name, cls_scope_id, symbol_table, scope_tree, import_res_result)
            a_rng = attr.range
            rec_a, res_a = self._create_reference(
                symbol_name=attr.name,
                kind=ReferenceKind.VARIABLE_DEFINITION,
                scope_id=cls_scope_id,
                file_path=file_path,
                target_symbol=attr_sym,
                line=a_rng.start.line if a_rng else 1,
                column=a_rng.start.column if a_rng else 0,
                end_line=a_rng.end.line if a_rng else 1,
                end_column=a_rng.end.column if a_rng else 10,
                is_definition=True,
                is_write=True,
            )
            records.append(rec_a)
            resolutions.append(res_a)

        # Process Methods inside class
        for method in cls.methods:
            m_records, m_resolutions = self._process_function(
                method, file_path, symbol_table, scope_tree, import_res_result, cls_scope_id, is_method=True
            )
            records.extend(m_records)
            resolutions.extend(m_resolutions)

        return records, resolutions

    def _process_function(
        self,
        fn: ExtractedFunction,
        file_path: str,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult],
        parent_scope_id: str,
        is_method: bool = False,
    ) -> Tuple[List[ReferenceRecord], List[ReferenceResolution]]:
        records: List[ReferenceRecord] = []
        resolutions: List[ReferenceResolution] = []

        fn_scope = next(
            (s for s in scope_tree.scopes.values() if s.kind in ("function", "lambda") and s.name == f"function:{fn.name}" and s.file_path == file_path),
            None,
        )
        fn_scope_id = fn_scope.id if fn_scope else parent_scope_id

        # Function Definition Site Reference
        kind = ReferenceKind.METHOD_CALL if is_method else ReferenceKind.FUNCTION_DEFINITION
        fn_sym = self._resolve_name(fn.name, parent_scope_id, symbol_table, scope_tree, import_res_result)
        rng = fn.range

        rec, res = self._create_reference(
            symbol_name=fn.name,
            kind=kind,
            scope_id=parent_scope_id,
            file_path=file_path,
            target_symbol=fn_sym,
            line=rng.start.line if rng else 1,
            column=rng.start.column if rng else 0,
            end_line=rng.end.line if rng else 1,
            end_column=rng.end.column if rng else 10,
            is_definition=True,
        )
        records.append(rec)
        resolutions.append(res)

        # Process Function Parameters
        for param in fn.parameters:
            p_sym = self._resolve_name(param.name, fn_scope_id, symbol_table, scope_tree, import_res_result)
            rec_p, res_p = self._create_reference(
                symbol_name=param.name,
                kind=ReferenceKind.VARIABLE_DEFINITION,
                scope_id=fn_scope_id,
                file_path=file_path,
                target_symbol=p_sym,
                line=rng.start.line if rng else 1,
                column=rng.start.column if rng else 0,
                end_line=rng.end.line if rng else 1,
                end_column=rng.end.column if rng else 10,
                is_definition=True,
                is_write=True,
            )
            records.append(rec_p)
            resolutions.append(res_p)

        # Process Function Local Variables
        for var in fn.local_variables:
            v_sym = self._resolve_name(var.name, fn_scope_id, symbol_table, scope_tree, import_res_result)
            v_rng = var.range
            rec_v, res_v = self._create_reference(
                symbol_name=var.name,
                kind=ReferenceKind.VARIABLE_WRITE,
                scope_id=fn_scope_id,
                file_path=file_path,
                target_symbol=v_sym,
                line=v_rng.start.line if v_rng else (rng.start.line if rng else 1),
                column=v_rng.start.column if v_rng else 0,
                end_line=v_rng.end.line if v_rng else (rng.start.line if rng else 1),
                end_column=v_rng.end.column if v_rng else 10,
                is_write=True,
            )
            records.append(rec_v)
            resolutions.append(res_v)

        return records, resolutions

    # ------------------------------------------------------------------
    # Symbol Resolver Logic
    # ------------------------------------------------------------------

    def _resolve_name(
        self,
        name: str,
        scope_id: str,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult],
    ) -> Optional[Symbol]:
        """
        Resolve an identifier name to a `Symbol` using Lexical Scope, Imports, and SymbolTable.
        """
        # 1. Lexical Scope Lookup
        sym = scope_tree.lookup_symbol(scope_id, name, symbol_table)
        if sym:
            return sym

        # 2. Check Import Resolutions
        if import_res_result:
            for imp_res in import_res_result.resolutions.values():
                if imp_res.target_symbol_id:
                    target_sym = symbol_table.get_symbol(imp_res.target_symbol_id)
                    if target_sym and target_sym.name == name:
                        return target_sym

        # 3. Direct SymbolTable Lookup
        for s in symbol_table.symbols.values():
            if s.name == name:
                return s

        return None

    def _create_reference(
        self,
        symbol_name: str,
        kind: ReferenceKind,
        scope_id: str,
        file_path: str,
        target_symbol: Optional[Symbol],
        line: int,
        column: int,
        end_line: int,
        end_column: int,
        is_read: bool = False,
        is_write: bool = False,
        is_definition: bool = False,
        is_call: bool = False,
        is_attribute_access: bool = False,
        attribute_chain: Optional[List[str]] = None,
    ) -> Tuple[ReferenceRecord, ReferenceResolution]:
        rec = ReferenceRecord(
            repository_id=self.repository_id,
            file_path=file_path,
            symbol_id=target_symbol.id if target_symbol else None,
            symbol_name=symbol_name,
            kind=kind,
            scope_id=scope_id,
            line=line,
            column=column,
            end_line=end_line,
            end_column=end_column,
            is_read=is_read,
            is_write=is_write,
            is_definition=is_definition,
            is_call=is_call,
            is_attribute_access=is_attribute_access,
            attribute_chain=attribute_chain,
        )

        res = ReferenceResolution(
            reference_id=rec.id,
            symbol_id=target_symbol.id if target_symbol else None,
            symbol_fqn=target_symbol.fqn if target_symbol else None,
            scope_id=scope_id,
            is_resolved=target_symbol is not None,
            error_message=None if target_symbol else f"Unresolved reference to '{symbol_name}'",
        )

        return rec, res
