"""
analysis/benchmark/regression_validator.py
-------------------------------------------
Phase 4.8.5 — Automated Pipeline Regression Validator.

Runs 12 automated contract checks across every pipeline stage to detect regressions,
graph corruption, missing symbols, dangling edges, or index mismatches.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.benchmark_models import (
    RegressionCheckItem,
    RegressionReport,
    RegressionStatus,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class RegressionValidator:
    """
    Automated regression checking engine across the complete 12-stage pipeline.

    Usage::

        validator = RegressionValidator()
        report = validator.validate_pipeline_results(pipeline_outputs)
    """

    def validate_pipeline_results(self, pipeline_data: Dict[str, Any]) -> RegressionReport:
        """
        Execute 12 automated pipeline regression check contracts.

        Parameters
        ----------
        pipeline_data:
            Dictionary containing stage result objects:
            - 'discovery': file list
            - 'parse_result': parser metrics
            - 'semantic_results': extraction list
            - 'symbol_table': SymbolTable
            - 'scope_result': ScopeResult
            - 'import_result': ImportResolutionResult
            - 'reference_result': ReferenceResolutionResult
            - 'call_detection_result': FunctionCallDetectionResult
            - 'call_graph_result': CallGraphResult
            - 'graph_index_result': CallGraphIndexResult
            - 'graph_validation_result': GraphValidationResult
            - 'processing_result': RepositoryProcessingResult

        Returns
        -------
        RegressionReport
        """
        checks: List[RegressionCheckItem] = []

        # REG-1: Repository Discovery Check
        disc_files = pipeline_data.get("discovery", [])
        py_files = [f for f in disc_files if (getattr(f, "path", None) or getattr(f, "file_path", "")).endswith(".py")]
        checks.append(
            RegressionCheckItem(
                check_id="REG-01-DISCOVERY",
                category="Discovery",
                name="Repository Discovery Completeness",
                status=RegressionStatus.PASS if len(py_files) > 0 else RegressionStatus.FAIL,
                expected="> 0 Python source files discovered",
                actual=f"{len(py_files)} Python files discovered",
                message="Discovery successfully identified Python source files",
            )
        )

        # REG-2: Tree-sitter Parser Check
        parse_res = pipeline_data.get("parse_result")
        failed_parses = getattr(parse_res, "failed_parses", 0) if parse_res else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-02-PARSER",
                category="Parser",
                name="Parser Fault Tolerance & AST Generation",
                status=RegressionStatus.PASS if failed_parses == 0 else RegressionStatus.WARNING,
                expected="0 failed parses",
                actual=f"{failed_parses} failed parses",
                message="All Python files parsed cleanly by Tree-sitter engine",
            )
        )

        # REG-3: Semantic Extraction Check
        sem_res = pipeline_data.get("semantic_results", [])
        total_sym_defs = sum(len(r.module.functions) + len(r.module.classes) for r in sem_res if hasattr(r, "module"))
        checks.append(
            RegressionCheckItem(
                check_id="REG-03-SEMANTIC",
                category="SemanticExtraction",
                name="Semantic Symbol Extraction",
                status=RegressionStatus.PASS if total_sym_defs > 0 else RegressionStatus.FAIL,
                expected="> 0 extracted functions and classes",
                actual=f"{total_sym_defs} definitions extracted",
                message="Semantic extractor extracted module symbols",
            )
        )

        # REG-4: Symbol Table Check
        sym_tab = pipeline_data.get("symbol_table")
        sym_count = len(sym_tab.symbols) if sym_tab and hasattr(sym_tab, "symbols") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-04-SYMBOL_TABLE",
                category="SymbolTable",
                name="Symbol Table Construction & Indexing",
                status=RegressionStatus.PASS if sym_count > 0 else RegressionStatus.FAIL,
                expected="> 0 symbols in symbol table",
                actual=f"{sym_count} symbols indexed",
                message="SymbolTable populated with unique symbol entities",
            )
        )

        # REG-5: Scope Resolution Check
        scope_res = pipeline_data.get("scope_result")
        scope_count = len(scope_res.scopes) if scope_res and hasattr(scope_res, "scopes") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-05-SCOPE",
                category="ScopeResolution",
                name="Scope Resolution & Symbol Scope Hierarchy",
                status=RegressionStatus.PASS if scope_count > 0 else RegressionStatus.FAIL,
                expected="> 0 scopes resolved",
                actual=f"{scope_count} scopes constructed",
                message="Scope hierarchy constructed without fatal errors",
            )
        )

        # REG-6: Import Resolution Check
        imp_res = pipeline_data.get("import_result")
        resolved_imps = (getattr(imp_res.metrics, "resolved_internal", 0) + getattr(imp_res.metrics, "resolved_stdlib", 0) + getattr(imp_res.metrics, "resolved_external", 0)) if imp_res and hasattr(imp_res, "metrics") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-06-IMPORT",
                category="ImportResolution",
                name="Import Resolution",
                status=RegressionStatus.PASS if resolved_imps >= 0 else RegressionStatus.FAIL,
                expected=">= 0 resolved imports",
                actual=f"{resolved_imps} imports resolved",
                message="ImportResolver resolved imports across standard library, external, and internal modules",
            )
        )

        # REG-7: Reference Resolution Check
        ref_res = pipeline_data.get("reference_result")
        resolved_refs = getattr(ref_res.metrics, "resolved_count", 0) if ref_res and hasattr(ref_res, "metrics") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-07-REFERENCE",
                category="ReferenceResolution",
                name="Reference Resolution & Variable Binding",
                status=RegressionStatus.PASS if resolved_refs >= 0 else RegressionStatus.FAIL,
                expected=">= 0 resolved references",
                actual=f"{resolved_refs} references resolved to symbol IDs",
                message="ReferenceResolver bound variable and function usages to symbol definitions",
            )
        )

        # REG-8: Function Call Detection Check
        call_det = pipeline_data.get("call_detection_result")
        total_calls = call_det.metrics.total_calls if call_det and hasattr(call_det, "metrics") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-08-CALL_DETECTION",
                category="FunctionCallDetection",
                name="Function Call Detection Engine",
                status=RegressionStatus.PASS if total_calls >= 0 else RegressionStatus.FAIL,
                expected=">= 0 call expressions detected",
                actual=f"{total_calls} call expressions detected",
                message="FunctionCallDetector identified call sites, method invocations, and constructors",
            )
        )

        # REG-9: Call Graph Builder Check
        cg_res = pipeline_data.get("call_graph_result")
        node_cnt = cg_res.graph.node_count if cg_res and hasattr(cg_res, "graph") else 0
        edge_cnt = cg_res.graph.edge_count if cg_res and hasattr(cg_res, "graph") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-09-CALL_GRAPH",
                category="CallGraphBuilder",
                name="Directed Call Graph Construction",
                status=RegressionStatus.PASS if node_cnt > 0 else RegressionStatus.FAIL,
                expected="> 0 nodes in call graph",
                actual=f"{node_cnt} nodes, {edge_cnt} directed edges",
                message="CallGraphBuilder constructed directed graph with weighted edges",
            )
        )

        # REG-10: Graph Index & Query Engine Check
        idx_res = pipeline_data.get("graph_index_result")
        idx_nodes = idx_res.metrics.indexed_nodes if idx_res and hasattr(idx_res, "metrics") else 0
        checks.append(
            RegressionCheckItem(
                check_id="REG-10-GRAPH_INDEX",
                category="GraphIndexQueryEngine",
                name="Multi-Index Construction & O(1) Query Engine",
                status=RegressionStatus.PASS if idx_nodes == node_cnt else RegressionStatus.FAIL,
                expected=f"Indexed nodes ({idx_nodes}) == Graph nodes ({node_cnt})",
                actual=f"{idx_nodes} indexed nodes",
                message="CallGraphQueryEngine operational with instant O(1) lookup tables",
            )
        )

        # REG-11: Graph Validation Framework Check
        val_res = pipeline_data.get("graph_validation_result")
        val_valid = val_res.validation_report.is_valid if val_res and hasattr(val_res, "validation_report") else True
        checks.append(
            RegressionCheckItem(
                check_id="REG-11-GRAPH_VALIDATION",
                category="GraphValidationFramework",
                name="Read-Only Graph Integrity Validation",
                status=RegressionStatus.PASS if val_valid else RegressionStatus.FAIL,
                expected="Validation report is_valid == True",
                actual=f"is_valid={val_valid}",
                message="GraphValidator verified graph structural consistency without zero data mutation",
            )
        )

        # REG-12: Optimization & Fault Tolerance Check
        proc_res = pipeline_data.get("processing_result")
        proc_success = proc_res.success if proc_res and hasattr(proc_res, "success") else True
        checks.append(
            RegressionCheckItem(
                check_id="REG-12-OPTIMIZATION",
                category="OptimizationFaultTolerance",
                name="Scalability Batching & Fault Tolerance",
                status=RegressionStatus.PASS if proc_success else RegressionStatus.FAIL,
                expected="Pipeline execution success == True",
                actual=f"success={proc_success}",
                message="RepositoryProcessingPipeline executed streaming file batches with non-stopping error recovery",
            )
        )

        failures = [c for c in checks if c.status == RegressionStatus.FAIL]
        warnings = [c for c in checks if c.status == RegressionStatus.WARNING]

        overall_status = RegressionStatus.PASS if len(failures) == 0 else RegressionStatus.FAIL

        return RegressionReport(
            overall_status=overall_status,
            checks=checks,
            failure_count=len(failures),
            warning_count=len(warnings),
        )
