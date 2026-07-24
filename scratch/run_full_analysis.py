"""
scratch/run_full_analysis.py
----------------------------
End-to-End Test Script executing DevBrain Repository Analyzer V2 pipeline on Trading_bot repo.
"""

import json
import os
import sys
import psutil
import time
import traceback

sys.path.insert(0, r"d:\devbrain\backend\repository_analyzer_v2")

from core.execution_context import ExecutionContext
from models.job import AnalysisJob
from models.repository import RepositoryFile


def make_repo_file(path: str, content: str) -> RepositoryFile:
    return RepositoryFile(
        path=path,
        name=os.path.basename(path),
        extension=path.rsplit(".", 1)[-1] if "." in path else "py",
        language="python",
        size_bytes=len(content.encode()),
        line_count=content.count("\n") + 1,
        content=content,
    )


def make_job(content: str, path: str) -> AnalysisJob:
    return AnalysisJob(
        repository_id="trading_bot_repo",
        file=make_repo_file(path, content),
        language="python",
    )
from plugins.python.python_parser_plugin import PythonParserPlugin
from plugins.python.semantic_extractor import PythonSemanticExtractor
from analysis.symbol_table.symbol_builder import SymbolTableBuilder
from analysis.symbol_table.symbol_validator import SymbolTableValidator
from analysis.scope_resolution.scope_resolver import ScopeResolver
from analysis.scope_resolution.scope_tree import ScopeTree
from analysis.import_resolution.import_resolver import ImportResolver
from analysis.reference_resolution.reference_resolver import ReferenceResolver


def measure_memory_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def main():
    repo_path = r"d:\devbrain\Trading_bot"
    repo_id = "trading_bot_repo"

    start_total_time = time.perf_counter()
    initial_mem = measure_memory_mb()
    peak_mem = initial_mem

    print(f"==========================================================")
    print(f" Starting DevBrain Analyzer V2 End-to-End Benchmark")
    print(f" Target Repository: {repo_path}")
    print(f" Initial Memory RSS: {initial_mem:.2f} MB")
    print(f"==========================================================\n")

    # ------------------------------------------------------------------
    # PHASE 1: Repository Discovery
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    discovered_files: List[str] = []
    language_breakdown: Dict[str, int] = {}
    total_bytes = 0

    for root, dirs, files in os.walk(repo_path):
        if ".git" in root:
            continue
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            discovered_files.append(rel_path)

            ext = os.path.splitext(file)[1].lower() or "no_extension"
            language_breakdown[ext] = language_breakdown.get(ext, 0) + 1
            total_bytes += os.path.getsize(full_path)

    phase1_duration_ms = (time.perf_counter() - t0) * 1000.0
    python_files = [f for f in discovered_files if f.endswith(".py")]

    print(f"[Phase 1: Repository Discovery]")
    print(f"  - Total files discovered: {len(discovered_files)}")
    print(f"  - Python source files: {len(python_files)}")
    print(f"  - Total codebase size: {total_bytes / 1024:.2f} KB")
    print(f"  - Language breakdown: {json.dumps(language_breakdown)}")
    print(f"  - Duration: {phase1_duration_ms:.2f} ms\n")

    # ------------------------------------------------------------------
    # PHASE 2: Parser Infrastructure & Tree-sitter AST
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    python_plugin = PythonParserPlugin()
    python_plugin.initialize()

    parse_results: List[Any] = []
    parse_success_count = 0
    parse_error_count = 0
    total_ast_nodes = 0

    for rel_file in python_files:
        abs_file = os.path.join(repo_path, rel_file)
        try:
            with open(abs_file, "r", encoding="utf-8", errors="replace") as f:
                source_code = f.read()

            job = make_job(source_code, rel_file)
            context = ExecutionContext(job=job, worker=None, pipeline_context=None)
            result = python_plugin.parse(job, context)
            parse_results.append((rel_file, result))

            if result.status == "success" or (hasattr(result, "ast_root") and result.ast_root is not None):
                parse_success_count += 1
                if result.ast_root:
                    if hasattr(result.ast_root, "node_count"):
                        total_ast_nodes += result.ast_root.node_count
                    elif isinstance(result.ast_root, dict):
                        total_ast_nodes += result.ast_root.get("node_count", 0)
            else:
                parse_error_count += 1
        except Exception as e:
            parse_error_count += 1
            print(f"  ! Parse exception on {rel_file}: {e}")

    phase2_duration_ms = (time.perf_counter() - t0) * 1000.0
    peak_mem = max(peak_mem, measure_memory_mb())

    print(f"[Phase 2: Tree-sitter Parser Engine]")
    print(f"  - Parsed files: {len(parse_results)}")
    print(f"  - Successful parses: {parse_success_count}")
    print(f"  - Failed parses: {parse_error_count}")
    print(f"  - Total AST nodes generated: {total_ast_nodes}")
    print(f"  - Duration: {phase2_duration_ms:.2f} ms\n")

    # ------------------------------------------------------------------
    # PHASE 3: Python Semantic Extraction
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    semantic_extractor = PythonSemanticExtractor()
    semantic_results: List[Any] = []
    total_classes = 0
    total_functions = 0
    total_variables = 0
    total_extracted_imports = 0

    for rel_file, parse_res in parse_results:
        try:
            sem_res = semantic_extractor.extract_result(parse_res)
            semantic_results.append(sem_res)

            mod = sem_res.module
            total_classes += len(mod.classes)
            total_functions += len(mod.functions)
            for c in mod.classes:
                total_functions += len(c.methods)
                total_variables += len(c.class_attributes)
            total_variables += len(mod.global_variables) + len(mod.constants)
            total_extracted_imports += len(mod.imports)
        except Exception as e:
            print(f"  ! Semantic extraction exception on {rel_file}: {e}")

    phase3_duration_ms = (time.perf_counter() - t0) * 1000.0
    peak_mem = max(peak_mem, measure_memory_mb())

    print(f"[Phase 3: Python Semantic Extraction]")
    print(f"  - Extracted module results: {len(semantic_results)}")
    print(f"  - Extracted classes: {total_classes}")
    print(f"  - Extracted functions/methods: {total_functions}")
    print(f"  - Extracted variables/constants: {total_variables}")
    print(f"  - Extracted raw imports: {total_extracted_imports}")
    print(f"  - Duration: {phase3_duration_ms:.2f} ms\n")

    # ------------------------------------------------------------------
    # PHASE 4: Symbol Table & Symbol Index
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    sym_builder = SymbolTableBuilder(repository_id=repo_id)
    symbol_table = sym_builder.build_from_results(semantic_results)
    symbol_table.freeze()

    sym_validator = SymbolTableValidator()
    sym_val_report = sym_validator.validate(symbol_table)

    phase4_duration_ms = (time.perf_counter() - t0) * 1000.0
    peak_mem = max(peak_mem, measure_memory_mb())

    print(f"[Phase 4: Symbol Table & Symbol Index]")
    print(f"  - Total symbols created: {len(symbol_table.symbols)}")
    print(f"  - Symbol table frozen: {symbol_table.is_frozen}")
    print(f"  - Symbol validation report: valid={sym_val_report.is_valid}, errors={sym_val_report.error_count}, warnings={sym_val_report.warning_count}")
    print(f"  - Duration: {phase4_duration_ms:.2f} ms\n")

    # ------------------------------------------------------------------
    # PHASE 5: Scope Resolution Engine
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    scope_resolver = ScopeResolver(repository_id=repo_id)
    scope_res_result = scope_resolver.resolve_results(semantic_results, symbol_table)

    scope_tree = ScopeTree(
        repository_id=repo_id,
        scopes=scope_res_result.scopes,
        root_scope_ids=scope_res_result.root_scope_ids,
    )

    phase5_duration_ms = (time.perf_counter() - t0) * 1000.0
    peak_mem = max(peak_mem, measure_memory_mb())

    print(f"[Phase 5: Scope Resolution Engine]")
    print(f"  - Total scopes created: {len(scope_res_result.scopes)}")
    print(f"  - Max scope nesting depth: {scope_res_result.metrics.max_nesting_depth}")
    print(f"  - Name shadowing occurrences: {len(scope_res_result.shadowing_records)}")
    print(f"  - Scope warnings: {len(scope_res_result.warnings)}, errors: {len(scope_res_result.errors)}")
    print(f"  - Duration: {phase5_duration_ms:.2f} ms\n")

    # ------------------------------------------------------------------
    # PHASE 6: Import Resolution Engine
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    import_resolver = ImportResolver(repository_id=repo_id)
    import_res_result = import_resolver.resolve_results(semantic_results, symbol_table)

    phase6_duration_ms = (time.perf_counter() - t0) * 1000.0
    peak_mem = max(peak_mem, measure_memory_mb())

    print(f"[Phase 6: Import Resolution Engine]")
    print(f"  - Total import statements: {import_res_result.metrics.total_imports}")
    print(f"  - Resolved internal repo imports: {import_res_result.metrics.resolved_internal}")
    print(f"  - Resolved standard library imports: {import_res_result.metrics.resolved_stdlib}")
    print(f"  - Resolved external library imports: {import_res_result.metrics.resolved_external}")
    print(f"  - Unresolved imports: {import_res_result.metrics.unresolved_count}")
    print(f"  - Relative imports: {import_res_result.metrics.relative_count}")
    print(f"  - Import warnings: {len(import_res_result.warnings)}, errors: {len(import_res_result.errors)}")
    print(f"  - Duration: {phase6_duration_ms:.2f} ms\n")

    # ------------------------------------------------------------------
    # PHASE 7: Reference Resolution Engine
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    reference_resolver = ReferenceResolver(repository_id=repo_id)
    ref_res_result = reference_resolver.resolve_results(
        semantic_results, symbol_table, scope_tree, import_res_result
    )

    phase7_duration_ms = (time.perf_counter() - t0) * 1000.0
    peak_mem = max(peak_mem, measure_memory_mb())

    total_duration_ms = (time.perf_counter() - start_total_time) * 1000.0

    print(f"[Phase 7: Reference Resolution Engine]")
    print(f"  - Total references recorded: {ref_res_result.metrics.total_references}")
    print(f"  - Resolved references: {ref_res_result.metrics.resolved_count}")
    print(f"  - Unresolved references: {ref_res_result.metrics.unresolved_count}")
    print(f"  - Read references: {ref_res_result.metrics.read_count}")
    print(f"  - Write references: {ref_res_result.metrics.write_count}")
    print(f"  - Call references: {ref_res_result.metrics.call_count}")
    print(f"  - Definition site references: {ref_res_result.metrics.definition_count}")
    print(f"  - Reference warnings: {len(ref_res_result.warnings)}, errors: {len(ref_res_result.errors)}")
    print(f"  - Duration: {phase7_duration_ms:.2f} ms\n")

    print(f"==========================================================")
    print(f" COMPLETE PIPELINE EXECUTION SUMMARY")
    print(f"==========================================================")
    print(f"  - Total Execution Duration: {total_duration_ms:.2f} ms ({total_duration_ms/1000.0:.2f}s)")
    print(f"  - Peak Memory Usage (RSS): {peak_mem:.2f} MB")
    print(f"==========================================================")

    # Export Full Results to JSON for Report Generator
    analysis_data = {
        "repo_path": repo_path,
        "total_files": len(discovered_files),
        "python_files": len(python_files),
        "total_code_bytes": total_bytes,
        "language_breakdown": language_breakdown,
        "parse_success_count": parse_success_count,
        "parse_error_count": parse_error_count,
        "total_ast_nodes": total_ast_nodes,
        "semantic_entities": {
            "classes": total_classes,
            "functions": total_functions,
            "variables": total_variables,
            "raw_imports": total_extracted_imports,
        },
        "symbol_metrics": {
            "total_symbols": len(symbol_table.symbols),
            "is_valid": sym_val_report.is_valid,
            "error_count": sym_val_report.error_count,
            "warning_count": sym_val_report.warning_count,
            "issues": [i.model_dump() for i in sym_val_report.issues],
        },
        "scope_metrics": {
            "total_scopes": len(scope_res_result.scopes),
            "max_nesting_depth": scope_res_result.metrics.max_nesting_depth,
            "shadowing_count": len(scope_res_result.shadowing_records),
            "warnings": scope_res_result.warnings,
            "errors": scope_res_result.errors,
            "shadowing_records": [s.model_dump() for s in scope_res_result.shadowing_records],
        },
        "import_metrics": import_res_result.metrics.model_dump(),
        "import_warnings": import_res_result.warnings,
        "import_errors": import_res_result.errors,
        "reference_metrics": ref_res_result.metrics.model_dump(),
        "reference_warnings": ref_res_result.warnings,
        "reference_errors": ref_res_result.errors,
        "phase_durations_ms": {
            "phase1_discovery": phase1_duration_ms,
            "phase2_parser": phase2_duration_ms,
            "phase3_semantic": phase3_duration_ms,
            "phase4_symbol_table": phase4_duration_ms,
            "phase5_scope_resolution": phase5_duration_ms,
            "phase6_import_resolution": phase6_duration_ms,
            "phase7_reference_resolution": phase7_duration_ms,
            "total": total_duration_ms,
        },
        "peak_memory_mb": peak_mem,
    }

    out_file = r"d:\devbrain\scratch\trading_bot_analysis_data.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(analysis_data, f, indent=2)

    print(f"\nSaved raw analysis data to: {out_file}")


if __name__ == "__main__":
    main()
