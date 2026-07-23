"""
analysis/reference_resolution/reference_resolver.py
---------------------------------------------------
Phase 4.7 — Reference Resolution Coordinator.

Main entry point that coordinates `ReferenceBuilder`, `ReferenceIndex`, and `ReferenceValidator`
to generate a unified `ReferenceResolutionResult` across a repository.

Design Principles
-----------------
- **Clean Architecture Pipeline**: Coordinates reference building, indexing, validation, and telemetry.
- **Robust Error Recovery**: Captures validation warnings and errors without crashing.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from models.import_models import ImportResolutionResult
from models.reference_models import (
    ReferenceMetrics,
    ReferenceResolutionResult,
)
from analysis.scope_resolution.scope_tree import ScopeTree
from models.semantic import SemanticExtractionResult
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.reference_resolution.reference_builder import ReferenceBuilder
from analysis.reference_resolution.reference_index import ReferenceIndex
from analysis.reference_resolution.reference_validator import ReferenceValidator
from utils.logger import get_logger

logger = get_logger(__name__)


class ReferenceResolver:
    """
    Coordinator engine for performing repository reference resolution.

    Usage::

        resolver = ReferenceResolver(repository_id="repo1")
        result = resolver.resolve_results([sem_result], symbol_table, scope_tree, import_res)
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._builder = ReferenceBuilder(repository_id=repository_id)
        self._validator = ReferenceValidator()

    def resolve_result(
        self,
        extraction_result: SemanticExtractionResult,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res: Optional[ImportResolutionResult] = None,
    ) -> ReferenceResolutionResult:
        """Resolve references for a single `SemanticExtractionResult`."""
        return self.resolve_results([extraction_result], symbol_table, scope_tree, import_res)

    def resolve_results(
        self,
        extraction_results: List[SemanticExtractionResult],
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res: Optional[ImportResolutionResult] = None,
    ) -> ReferenceResolutionResult:
        """
        Resolve identifier usage references across multiple `SemanticExtractionResult` objects.

        Parameters
        ----------
        extraction_results:
            List of `SemanticExtractionResult` objects.
        symbol_table:
            Repository `SymbolTable`.
        scope_tree:
            Lexical `ScopeTree`.
        import_res:
            Optional `ImportResolutionResult`.

        Returns
        -------
        ReferenceResolutionResult
        """
        start_time = time.perf_counter()

        ref_index = ReferenceIndex()
        metrics = ReferenceMetrics()

        for res in extraction_results:
            records, resolutions = self._builder.build_from_module(
                res.module, symbol_table, scope_tree, import_res
            )

            for rec, resolution in zip(records, resolutions):
                ref_index.add_reference(rec, resolution)

                # Collect Metrics
                metrics.total_references += 1
                if resolution.is_resolved:
                    metrics.resolved_count += 1
                else:
                    metrics.unresolved_count += 1

                if rec.is_read:
                    metrics.read_count += 1
                if rec.is_write:
                    metrics.write_count += 1
                if rec.is_call:
                    metrics.call_count += 1
                if rec.is_attribute_access:
                    metrics.attribute_count += 1
                if rec.is_definition:
                    metrics.definition_count += 1

        val_report = self._validator.validate(ref_index, symbol_table, scope_tree)
        warnings = [i.message for i in val_report.issues if i.severity == "warning"]
        errors = [i.message for i in val_report.issues if i.severity == "error"]

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics.build_duration_ms = round(duration_ms, 3)
        metrics.memory_bytes = self._get_memory_bytes()

        return ReferenceResolutionResult(
            repository_id=self.repository_id,
            references=ref_index.references,
            resolutions=ref_index.resolutions,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
        )

    @staticmethod
    def _get_memory_bytes() -> int:
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            return 0
