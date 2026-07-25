"""
core/symbol_builder/pipeline.py
--------------------------------
Symbol Pipeline Execution Engine orchestrating Steps 3.2 through 3.5.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from core.namespaces import NamespaceBuilder, NamespaceTree
from core.symbol_builder.diagnostics import PipelineDiagnostics
from core.symbol_builder.models import SemanticRepository
from core.symbol_builder.statistics import SemanticRepositoryStatistics
from core.symbol_builder.validator import PipelineValidator
from core.symbol_extractor import RawSymbolCollection, SymbolExtractor
from core.symbol_identity import CanonicalSymbolCollection, SymbolIdentityBuilder
from core.symbol_table import SymbolTable, SymbolTableBuilder
from models.parser import ParserResult


class SymbolPipelineEngine:
    """
    Sequential Pipeline Execution Engine orchestrating Step 3 Symbol Builders.
    """

    def execute(
        self,
        repository_id: str,
        parser_results: List[ParserResult],
        workspace: Optional[Any] = None
    ) -> SemanticRepository:
        pipeline_start = time.perf_counter()
        timings: dict[str, float] = {}

        # -------------------------------------------------------------------
        # Stage 1: Namespace Builder (Step 3.2)
        # -------------------------------------------------------------------
        t0 = time.perf_counter()
        ns_builder = NamespaceBuilder()
        try:
            ns_tree = ns_builder.build_tree(parser_results, repository_id)
        except Exception as e:
            ns_tree = NamespaceTree(repository_id=repository_id, root_id=ns_builder._make_root_id if hasattr(ns_builder, "_make_root_id") else None)  # type: ignore
        timings["namespace_builder_ms"] = (time.perf_counter() - t0) * 1000.0

        # -------------------------------------------------------------------
        # Stage 2: Symbol Extractor (Step 3.3)
        # -------------------------------------------------------------------
        t0 = time.perf_counter()
        extractor = SymbolExtractor()
        try:
            raw_coll = extractor.extract_symbols(parser_results, ns_tree)
        except Exception as e:
            raw_coll = RawSymbolCollection(repository_id=repository_id)
        timings["symbol_extractor_ms"] = (time.perf_counter() - t0) * 1000.0

        # -------------------------------------------------------------------
        # Stage 3: Symbol Identity Builder (Step 3.4)
        # -------------------------------------------------------------------
        t0 = time.perf_counter()
        identity_builder = SymbolIdentityBuilder()
        try:
            can_coll = identity_builder.build_canonical_symbols(raw_coll, ns_tree)
        except Exception as e:
            can_coll = CanonicalSymbolCollection(repository_id=repository_id)
        timings["symbol_identity_ms"] = (time.perf_counter() - t0) * 1000.0

        # -------------------------------------------------------------------
        # Stage 4: Symbol Table Builder (Step 3.5)
        # -------------------------------------------------------------------
        t0 = time.perf_counter()
        table_builder = SymbolTableBuilder()
        try:
            sym_table = table_builder.build_symbol_table(can_coll, ns_tree)
        except Exception as e:
            sym_table = SymbolTable(repository_id=repository_id)
        timings["symbol_table_ms"] = (time.perf_counter() - t0) * 1000.0

        total_pipeline_ms = (time.perf_counter() - pipeline_start) * 1000.0
        timings["total_pipeline_ms"] = total_pipeline_ms

        # -------------------------------------------------------------------
        # Diagnostic & Statistics Aggregation
        # -------------------------------------------------------------------
        aggregated_diagnostics = PipelineDiagnostics(
            namespace_diagnostics=ns_tree.diagnostics,
            extraction_diagnostics=raw_coll.diagnostics,
            identity_diagnostics=can_coll.diagnostics,
            symbol_table_diagnostics=sym_table.diagnostics
        )

        aggregated_statistics = SemanticRepositoryStatistics(
            total_files=len(parser_results),
            total_namespaces=len(ns_tree.nodes),
            total_raw_symbols=len(raw_coll.symbols),
            total_canonical_symbols=len(can_coll.symbols),
            total_indexed_symbols=sym_table.count(),
            stage_timings_ms=timings,
            duplicates_detected=can_coll.statistics.duplicates_detected,
            overloads_detected=can_coll.statistics.overloads_detected
        )

        repo = SemanticRepository(
            repository_id=repository_id,
            workspace=workspace,
            namespace_tree=ns_tree,
            canonical_symbols=can_coll,
            symbol_table=sym_table,
            statistics=aggregated_statistics,
            diagnostics=aggregated_diagnostics,
            pipeline_metadata={"file_count": len(parser_results)}
        )

        # -------------------------------------------------------------------
        # Pipeline Validation Check
        # -------------------------------------------------------------------
        final_diags = PipelineValidator.validate(repo)
        if final_diags.pipeline_records:
            repo = SemanticRepository(
                repository_id=repo.repository_id,
                workspace=repo.workspace,
                namespace_tree=repo.namespace_tree,
                canonical_symbols=repo.canonical_symbols,
                symbol_table=repo.symbol_table,
                statistics=repo.statistics,
                diagnostics=final_diags,
                pipeline_metadata=repo.pipeline_metadata
            )

        return repo
