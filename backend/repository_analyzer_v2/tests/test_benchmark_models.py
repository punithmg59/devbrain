"""
tests/test_benchmark_models.py
-------------------------------
Unit tests for benchmark data models — verifying Pydantic V2 instantiation and JSON serialization.
"""

from models.benchmark_models import (
    MemoryMetrics,
    ProductionReadinessReport,
    ProductionReadinessStatus,
    RegressionCheckItem,
    RegressionReport,
    RegressionStatus,
    RepositoryBenchmarkResult,
    RepositoryBenchmarkTarget,
    RepositorySizeCategory,
    ScalabilityMetrics,
)


class TestBenchmarkModels:
    def test_repository_benchmark_target_instantiation(self):
        target = RepositoryBenchmarkTarget(
            name="FastAPI",
            path="d:/devbrain/fastapi",
            category=RepositorySizeCategory.LARGE,
        )
        assert target.name == "FastAPI"
        assert target.category == RepositorySizeCategory.LARGE

    def test_regression_report_instantiation(self):
        item = RegressionCheckItem(
            check_id="REG-01",
            category="Discovery",
            name="Discovery Check",
            status=RegressionStatus.PASS,
            expected="> 0 files",
            actual="1127 files",
            message="OK",
        )
        report = RegressionReport(
            overall_status=RegressionStatus.PASS,
            checks=[item],
            failure_count=0,
        )
        assert report.overall_status == RegressionStatus.PASS
        assert len(report.checks) == 1

    def test_production_readiness_report_instantiation(self):
        report = ProductionReadinessReport(
            overall_status=ProductionReadinessStatus.PRODUCTION_READY,
            readiness_score=100.0,
            key_strengths=["Clean pipeline execution"],
        )
        assert report.overall_status == ProductionReadinessStatus.PRODUCTION_READY
        assert report.readiness_score == 100.0
