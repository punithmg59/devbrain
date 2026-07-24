"""
models/benchmark_models.py
--------------------------
Phase 4.8.5 — Language-Independent Benchmark & Production Readiness Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
repository targets, stage performance timings, memory RSS metrics, scalability throughput,
automated regression check reports, production readiness evaluation, and benchmark suite results.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Telemetry-Driven**: High-resolution performance metrics and production readiness scoring.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RepositorySizeCategory(str, Enum):
    """Size classification for benchmark target repositories."""
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    ENTERPRISE = "Enterprise"


class RegressionStatus(str, Enum):
    """Status for automated pipeline regression check items."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class ProductionReadinessStatus(str, Enum):
    """Overall status for production readiness evaluation."""
    PRODUCTION_READY = "PRODUCTION_READY"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"


class RepositoryBenchmarkTarget(BaseModel):
    """Configuration identifying a target repository to benchmark."""
    name: str = Field(..., description="Repository identifier name")
    path: str = Field(..., description="Local filesystem path to repository root")
    category: RepositorySizeCategory = Field(default=RepositorySizeCategory.MEDIUM, description="Repository size classification")
    description: str = Field(default="", description="Repository description")


class StagePerformance(BaseModel):
    """Performance telemetry for a single pipeline execution stage."""
    stage: str = Field(..., description="Pipeline stage name")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Stage duration in milliseconds")
    memory_rss_mb: float = Field(default=0.0, ge=0.0, description="Process RSS memory at stage end in megabytes")
    objects_processed: int = Field(default=0, ge=0, description="Count of objects processed during stage")
    throughput: float = Field(default=0.0, ge=0.0, description="Stage processing throughput in items/sec")


class MemoryMetrics(BaseModel):
    """Detailed memory consumption footprint and growth metrics."""
    initial_rss_mb: float = Field(default=0.0, ge=0.0, description="Initial RSS memory before benchmark in MB")
    peak_rss_mb: float = Field(default=0.0, ge=0.0, description="Peak RSS memory recorded during execution in MB")
    final_rss_mb: float = Field(default=0.0, ge=0.0, description="Final RSS memory after execution in MB")
    memory_growth_mb: float = Field(default=0.0, description="Net memory growth in MB")
    memory_reclaimed_mb: float = Field(default=0.0, ge=0.0, description="Memory reclaimed by GC in MB")


class ScalabilityMetrics(BaseModel):
    """High-level throughput and scalability rates."""
    total_files: int = Field(default=0, ge=0, description="Total files analyzed")
    total_loc: int = Field(default=0, ge=0, description="Total lines of Python code")
    total_nodes: int = Field(default=0, ge=0, description="Total graph nodes created")
    total_edges: int = Field(default=0, ge=0, description="Total graph edges created")
    total_indexes: int = Field(default=0, ge=0, description="Total index entries created")
    files_per_sec: float = Field(default=0.0, ge=0.0, description="Processing throughput in files/sec")
    loc_per_sec: float = Field(default=0.0, ge=0.0, description="Processing throughput in LOC/sec")
    nodes_per_sec: float = Field(default=0.0, ge=0.0, description="Node generation rate in nodes/sec")
    edges_per_sec: float = Field(default=0.0, ge=0.0, description="Edge generation rate in edges/sec")


class RegressionCheckItem(BaseModel):
    """Individual pipeline regression check item."""
    check_id: str = Field(..., description="Unique check identifier, e.g. 'REG-DISC-01'")
    category: str = Field(..., description="Stage category")
    name: str = Field(..., description="Human-readable check name")
    status: RegressionStatus = Field(default=RegressionStatus.PASS, description="Check outcome status")
    expected: str = Field(..., description="Expected contract requirement")
    actual: str = Field(..., description="Empirical measured result")
    message: str = Field(..., description="Check status explanation")


class RegressionReport(BaseModel):
    """Automated regression testing report across all pipeline stages."""
    overall_status: RegressionStatus = Field(default=RegressionStatus.PASS, description="Overall regression status")
    checks: List[RegressionCheckItem] = Field(default_factory=list, description="List of all RegressionCheckItem objects")
    failure_count: int = Field(default=0, ge=0, description="Count of FAIL checks")
    warning_count: int = Field(default=0, ge=0, description="Count of WARNING checks")


class ProductionReadinessCategory(BaseModel):
    """Individual category evaluation for production readiness."""
    category_name: str = Field(..., description="Evaluation category, e.g. 'Correctness', 'Performance', 'Scalability'")
    status: str = Field(default="READY", description="'READY' or 'NEEDS_IMPROVEMENT'")
    score: float = Field(default=100.0, ge=0.0, le=100.0, description="Category readiness score (0-100)")
    summary: str = Field(..., description="Category evaluation summary")


class ProductionReadinessReport(BaseModel):
    """Comprehensive production readiness evaluation report."""
    overall_status: ProductionReadinessStatus = Field(
        default=ProductionReadinessStatus.PRODUCTION_READY,
        description="Final production readiness determination",
    )
    categories: List[ProductionReadinessCategory] = Field(default_factory=list, description="Breakdown across readiness categories")
    readiness_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Overall readiness score percentage")
    key_strengths: List[str] = Field(default_factory=list, description="List of key technical strengths")
    recommendations: List[str] = Field(default_factory=list, description="List of deployment recommendations")


class RepositoryBenchmarkResult(BaseModel):
    """Benchmark result for a single target repository."""
    result_id: str = Field(
        default_factory=lambda: f"benchres-{uuid.uuid4().hex[:12]}",
        description="Unique benchmark result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    target: RepositoryBenchmarkTarget = Field(..., description="Target repository details")
    success: bool = Field(default=True, description="True if analysis completed without unrecoverable errors")
    total_duration_ms: float = Field(default=0.0, ge=0.0, description="Total pipeline execution duration in ms")
    memory_metrics: MemoryMetrics = Field(default_factory=MemoryMetrics, description="Memory metrics")
    scalability_metrics: ScalabilityMetrics = Field(default_factory=ScalabilityMetrics, description="Scalability metrics")
    stage_timings: List[StagePerformance] = Field(default_factory=list, description="Stage timings breakdown")
    regression_report: RegressionReport = Field(default_factory=RegressionReport, description="Automated regression check report")
    readiness_report: ProductionReadinessReport = Field(default_factory=ProductionReadinessReport, description="Production readiness report")
    warnings: List[str] = Field(default_factory=list, description="Recorded warnings")
    errors: List[str] = Field(default_factory=list, description="Recorded errors")


class BenchmarkSuiteResult(BaseModel):
    """Aggregated result for a full benchmark suite execution."""
    suite_id: str = Field(
        default_factory=lambda: f"suite-{uuid.uuid4().hex[:12]}",
        description="Unique benchmark suite result ID",
    )
    timestamp: float = Field(default_factory=time.time, description="Benchmark execution timestamp")
    repository_results: List[RepositoryBenchmarkResult] = Field(default_factory=list, description="Individual repository results")
    overall_readiness_status: ProductionReadinessStatus = Field(
        default=ProductionReadinessStatus.PRODUCTION_READY,
        description="Overall suite production readiness status",
    )
    summary_metrics: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics across all repositories")
