"""
analysis/scope_resolution/scope_resolver.py
-------------------------------------------
Phase 4.5 — Scope Resolution Coordinator.

Main entry point that coordinates `ScopeBuilder` and `ScopeValidator` to generate
a unified `ScopeResolutionResult` for single files or multi-file repositories.

Design Principles
-----------------
- **Clean Architecture Pipeline**: Coordinates builder, tree, validator, and telemetry.
- **Robust Error Recovery**: Captures validation warnings and errors without crashing.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from models.scope import (
    ScopeMetrics,
    ScopeResolutionResult,
    ShadowingRelationship,
)
from models.semantic import ExtractedModule, SemanticExtractionResult
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_builder import ScopeBuilder
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.scope_resolution.scope_validator import ScopeValidator
from utils.logger import get_logger

logger = get_logger(__name__)


class ScopeResolver:
    """
    Coordinator engine for performing repository scope resolution.

    Usage::

        resolver = ScopeResolver(repository_id="repo1")
        result = resolver.resolve_result(semantic_result, symbol_table)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._builder = ScopeBuilder(repository_id=repository_id)
        self._validator = ScopeValidator()

    def resolve_result(
        self,
        extraction_result: SemanticExtractionResult,
        symbol_table: SymbolTable,
    ) -> ScopeResolutionResult:
        """Resolve scopes for a single `SemanticExtractionResult`."""
        return self.resolve_results([extraction_result], symbol_table)

    def resolve_module(
        self,
        module: ExtractedModule,
        symbol_table: SymbolTable,
    ) -> ScopeResolutionResult:
        """Resolve scopes for a single `ExtractedModule`."""
        start_time = time.perf_counter()

        tree, shadowing = self._builder.build_from_module(module, symbol_table)
        val_report = self._validator.validate(tree, symbol_table)

        warnings = [i.message for i in val_report.issues if i.severity == "warning"]
        errors = [i.message for i in val_report.issues if i.severity == "error"]

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        tree.metrics.build_duration_ms = round(duration_ms, 3)

        return ScopeResolutionResult(
            repository_id=self.repository_id,
            root_scope_ids=list(tree.root_scope_ids),
            scopes=tree.scopes,
            shadowing_records=shadowing,
            metrics=tree.metrics,
            warnings=warnings,
            errors=errors,
        )

    def resolve_results(
        self,
        extraction_results: List[SemanticExtractionResult],
        symbol_table: SymbolTable,
    ) -> ScopeResolutionResult:
        """
        Resolve scopes across multiple file `SemanticExtractionResult` objects.

        Parameters
        ----------
        extraction_results:
            List of `SemanticExtractionResult` objects.
        symbol_table:
            Repository `SymbolTable`.

        Returns
        -------
        ScopeResolutionResult
        """
        start_time = time.perf_counter()

        combined_tree = ScopeTree(repository_id=self.repository_id)
        all_shadowing: List[ShadowingRelationship] = []

        for res in extraction_results:
            tree, shadowing = self._builder.build_from_module(res.module, symbol_table)
            all_shadowing.extend(shadowing)

            for scope_id, scope in tree.scopes.items():
                combined_tree.add_scope(scope)

        val_report = self._validator.validate(combined_tree, symbol_table)
        warnings = [i.message for i in val_report.issues if i.severity == "warning"]
        errors = [i.message for i in val_report.issues if i.severity == "error"]

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        scopes_by_kind: Dict[str, int] = {}
        for sc in combined_tree.scopes.values():
            k = sc.kind.value
            scopes_by_kind[k] = scopes_by_kind.get(k, 0) + 1

        combined_tree.metrics = ScopeMetrics(
            total_scopes=len(combined_tree.scopes),
            scopes_by_kind=scopes_by_kind,
            max_nesting_depth=combined_tree.calculate_max_depth(),
            total_symbols_defined=sum(len(s.defined_symbol_ids) for s in combined_tree.scopes.values()),
            shadowing_count=len(all_shadowing),
            build_duration_ms=round(duration_ms, 3),
        )

        return ScopeResolutionResult(
            repository_id=self.repository_id,
            root_scope_ids=list(combined_tree.root_scope_ids),
            scopes=combined_tree.scopes,
            shadowing_records=all_shadowing,
            metrics=combined_tree.metrics,
            warnings=warnings,
            errors=errors,
        )
