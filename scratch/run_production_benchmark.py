"""
scratch/run_production_benchmark.py
------------------------------------
Phase 4.8.5 — Production Benchmark & Validation Suite Execution Script.

Executes the complete 12-stage pipeline benchmark on real-world repositories (Trading_bot and FastAPI),
runs 12-point automated regression checks, evaluates 11 production readiness categories,
and produces Production Readiness Reports.
"""

import json
import os
import sys
import time

# Ensure backend package is in python path
sys.path.insert(0, r"d:\devbrain\backend\repository_analyzer_v2")

from core.execution_context import ExecutionContext
from models.benchmark_models import ProductionReadinessStatus
from analysis.benchmark.benchmark_runner import BenchmarkRunner
from analysis.benchmark.benchmark_report import BenchmarkReportGenerator
from analysis.benchmark.repository_suite import RepositoryBenchmarkSuite


def main():
    print("==========================================================================")
    print(" DevBrain Analyzer V2 — Production Benchmark & Validation Suite Execution")
    print("==========================================================================")

    # 1. Initialize Suite Registry
    suite = RepositoryBenchmarkSuite.get_default_suite(workspace_root=r"d:\devbrain")
    targets = suite.get_targets()

    print(f"[Suite Registry] Loaded {len(targets)} target benchmark repositories:")
    for t in targets:
        print(f"  - [{t.category.value}] {t.name} ({t.path})")
    print()

    # 2. Run Benchmark Suite
    runner = BenchmarkRunner()
    suite_result = runner.run_suite(targets)

    report_gen = BenchmarkReportGenerator()

    # 3. Process & Display Results for Each Repository
    print("==========================================================================")
    print(" INDIVIDUAL REPOSITORY BENCHMARK RESULTS")
    print("==========================================================================")

    for res in suite_result.repository_results:
        print(f"\nTarget: {res.target.name} ({res.target.category.value})")
        print(f"  - Total Execution Duration: {res.total_duration_ms:.2f} ms ({res.total_duration_ms/1000.0:.2f}s)")
        print(f"  - Files Analyzed: {res.scalability_metrics.total_files:,}")
        print(f"  - Lines of Code (LOC): {res.scalability_metrics.total_loc:,}")
        print(f"  - Graph Nodes Created: {res.scalability_metrics.total_nodes:,}")
        print(f"  - Directed Edges Created: {res.scalability_metrics.total_edges:,}")
        print(f"  - Index Entries Built: {res.scalability_metrics.total_indexes:,}")
        print(f"  - Peak Memory RSS: {res.memory_metrics.peak_rss_mb:.2f} MB")
        print(f"  - Automated Regression Checks: overall_status={res.regression_report.overall_status.value} ({res.regression_report.failure_count} failures)")
        print(f"  - Production Readiness Status: {res.readiness_report.overall_status.value} (Score: {res.readiness_report.readiness_score}%)")

        # Generate & Write Individual Markdown Report
        md_text = report_gen.generate_markdown_report(res)
        report_filename = f"{res.target.name.lower()}_production_benchmark_report.md"
        report_path = os.path.join(r"d:\devbrain", report_filename)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"  - Saved markdown benchmark report to: {report_path}")

    print("\n==========================================================================")
    print(" OVERALL PRODUCTION READINESS EVALUATION")
    print("==========================================================================")
    print(f"  - Total Repositories Analyzed: {suite_result.summary_metrics.get('total_repositories_analyzed')}")
    print(f"  - Total Files Analyzed: {suite_result.summary_metrics.get('total_files_analyzed'):,}")
    print(f"  - Total Lines of Code (LOC): {suite_result.summary_metrics.get('total_loc_analyzed'):,}")
    print(f"  - Total Graph Nodes Generated: {suite_result.summary_metrics.get('total_nodes_generated'):,}")
    print(f"  - Total Directed Edges Generated: {suite_result.summary_metrics.get('total_edges_generated'):,}")
    print(f"  - Total Suite Execution Duration: {suite_result.summary_metrics.get('total_suite_duration_sec'):.2f}s")
    print(f"  - OVERALL STATUS: *** {suite_result.overall_readiness_status.value} ***")
    print("==========================================================================")

    if suite_result.overall_readiness_status == ProductionReadinessStatus.PRODUCTION_READY:
        print("\nSUCCESS: All pipeline contracts verified! DevBrain Repository Analyzer V2 is PRODUCTION READY!")
    else:
        print("\nWARNING: Some targets need improvement before production deployment.")


if __name__ == "__main__":
    main()
