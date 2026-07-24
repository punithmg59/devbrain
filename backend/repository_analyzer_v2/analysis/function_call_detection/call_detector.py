"""
analysis/function_call_detection/call_detector.py
--------------------------------------------------
Phase 4.7.2 — Function Call Detection Coordinator Engine.

Main pipeline coordinator that connects `CallBuilder`, `CallResolver`, `CallIndex`,
and `CallValidator` to extract, classify, resolve, and index all function calls
across a repository.

Design Principles
-----------------
- **Clean Pipeline Architecture**: Coordinates builder -> resolver -> index -> validator.
- **Multi-Resolution Integration**: Integrates Reference Resolution, Import Resolution,
  Re-Export Resolution, Lexical Scopes, and Symbol Table maps seamlessly.
- **Robust Telemetry & Validation**: Returns structured `FunctionCallDetectionResult`.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from models.ast import ASTRoot
from models.call_models import (
    CallRecord,
    FunctionCallDetectionResult,
)
from models.import_models import ImportResolutionResult
from models.reference_models import ReferenceResolutionResult
from models.semantic import SemanticExtractionResult
from analysis.symbol_table.symbol_table import SymbolTable
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.re_export_resolution.re_export_index import ReExportIndex
from analysis.function_call_detection.call_builder import CallBuilder
from analysis.function_call_detection.call_resolver import CallResolver
from analysis.function_call_detection.call_index import CallIndex
from analysis.function_call_detection.call_validator import CallValidator
from analysis.function_call_detection.metrics import compute_metrics
from utils.logger import get_logger

logger = get_logger(__name__)


class FunctionCallDetector:
    """
    Coordinator engine for performing repository function call detection.

    Usage::

        detector = FunctionCallDetector(repository_id="repo1")
        result = detector.detect_results(
            extraction_results, symbol_table, scope_tree, import_res, ref_res, export_index, ast_roots
        )
    """

    def __init__(self, repository_id: str = "repo") -> None:
        self.repository_id = repository_id
        self._builder = CallBuilder(repository_id=repository_id)
        self._resolver = CallResolver()
        self._validator = CallValidator()

    def detect_result(
        self,
        extraction_result: SemanticExtractionResult,
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult] = None,
        reference_res_result: Optional[ReferenceResolutionResult] = None,
        re_export_index: Optional[ReExportIndex] = None,
        ast_root: Optional[ASTRoot] = None,
    ) -> FunctionCallDetectionResult:
        """Detect calls for a single `SemanticExtractionResult`."""
        ast_roots = {extraction_result.file_path: ast_root} if ast_root else None
        return self.detect_results(
            extraction_results=[extraction_result],
            symbol_table=symbol_table,
            scope_tree=scope_tree,
            import_res_result=import_res_result,
            reference_res_result=reference_res_result,
            re_export_index=re_export_index,
            ast_roots=ast_roots,
        )

    def detect_results(
        self,
        extraction_results: List[SemanticExtractionResult],
        symbol_table: SymbolTable,
        scope_tree: ScopeTree,
        import_res_result: Optional[ImportResolutionResult] = None,
        reference_res_result: Optional[ReferenceResolutionResult] = None,
        re_export_index: Optional[ReExportIndex] = None,
        ast_roots: Optional[Dict[str, ASTRoot]] = None,
    ) -> FunctionCallDetectionResult:
        """
        Detect, classify, resolve, and index calls across multiple file `SemanticExtractionResult` objects.

        Parameters
        ----------
        extraction_results:
            List of `SemanticExtractionResult` objects.
        symbol_table:
            Repository `SymbolTable`.
        scope_tree:
            Repository `ScopeTree`.
        import_res_result:
            Optional `ImportResolutionResult`.
        reference_res_result:
            Optional `ReferenceResolutionResult`.
        re_export_index:
            Optional `ReExportIndex`.
        ast_roots:
            Optional map of file_path -> ASTRoot.

        Returns
        -------
        FunctionCallDetectionResult
        """
        start_time = time.perf_counter()
        raw_records: List[CallRecord] = []
        resolved_records: List[CallRecord] = []

        # 1. Extraction Phase (CallBuilder)
        for res in extraction_results:
            ast_root = ast_roots.get(res.file_path) if ast_roots else None
            records = self._builder.build_from_module(
                module=res.module,
                symbol_table=symbol_table,
                scope_tree=scope_tree,
                ast_root=ast_root,
            )
            raw_records.extend(records)

        # 2. Resolution Phase (CallResolver)
        for call in raw_records:
            resolved_call = self._resolver.resolve_call(
                call=call,
                symbol_table=symbol_table,
                scope_tree=scope_tree,
                import_res_result=import_res_result,
                reference_res_result=reference_res_result,
                export_index=re_export_index,
            )
            resolved_records.append(resolved_call)

        # 3. Indexing Phase (CallIndex)
        call_index = CallIndex()
        call_index.build(resolved_records)

        # 4. Validation Phase (CallValidator)
        val_report = self._validator.validate(call_index, symbol_table)
        warnings = [i.message for i in val_report.issues if i.severity == "warning"]
        errors = [i.message for i in val_report.issues if i.severity == "error"]

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = compute_metrics(
            call_records=resolved_records,
            build_duration_ms=duration_ms,
        )

        return FunctionCallDetectionResult(
            repository_id=self.repository_id,
            calls=call_index.calls,
            metrics=metrics,
            validation_report=val_report,
            warnings=warnings,
            errors=errors,
        )
