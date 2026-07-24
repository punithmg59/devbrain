"""
analysis/benchmark/__init__.py
------------------------------
Phase 4.8.5 — Production Benchmark & Validation Suite Package.

Exports benchmark runner, repository suite registry, automated regression validator,
report generator, production readiness models, and metrics.
"""

from models.benchmark_models import (
    BenchmarkSuiteResult,
    MemoryMetrics,
    ProductionReadinessCategory,
    ProductionReadinessReport,
    ProductionReadinessStatus,
    RegressionCheckItem,
    RegressionReport,
    RegressionStatus,
    RepositoryBenchmarkResult,
    RepositoryBenchmarkTarget,
    RepositorySizeCategory,
    ScalabilityMetrics,
    StagePerformance,
)
from analysis.benchmark.repository_suite import RepositoryBenchmarkSuite
from analysis.benchmark.regression_validator import RegressionValidator
from analysis.benchmark.benchmark_runner import BenchmarkRunner
from analysis.benchmark.benchmark_report import BenchmarkReportGenerator

__all__ = [
    # Main Suite & Runner
    "BenchmarkRunner",
    "RepositoryBenchmarkSuite",
    "RegressionValidator",
    "BenchmarkReportGenerator",
    # Models & Enums
    "RepositorySizeCategory",
    "RegressionStatus",
    "ProductionReadinessStatus",
    "RepositoryBenchmarkTarget",
    "StagePerformance",
    "MemoryMetrics",
    "ScalabilityMetrics",
    "RegressionCheckItem",
    "RegressionReport",
    "ProductionReadinessCategory",
    "ProductionReadinessReport",
    "RepositoryBenchmarkResult",
    "BenchmarkSuiteResult",
]
