"""
analysis/optimization/__init__.py
---------------------------------
Phase 4.8.4 — Large Repository Optimization & Fault Tolerance Package.

Exports optimization configuration, resource monitoring, progress tracking, streaming iterators,
fault-tolerant pipeline orchestrator, and data contracts.
"""

from models.optimization_models import (
    OptimizationMetrics,
    ProcessingIssue,
    ProcessingReport,
    ProcessingStage,
    ProgressSnapshot,
    RepositoryProcessingResult,
    ResourceSnapshot,
)
from analysis.optimization.optimization_config import OptimizationConfig
from analysis.optimization.progress_tracker import ProgressTracker
from analysis.optimization.repository_optimizer import RepositoryOptimizer
from analysis.optimization.resource_monitor import ResourceMonitor
from analysis.optimization.processing_pipeline import RepositoryProcessingPipeline

__all__ = [
    # Configuration
    "OptimizationConfig",
    # Components
    "ResourceMonitor",
    "ProgressTracker",
    "RepositoryOptimizer",
    "RepositoryProcessingPipeline",
    # Models
    "ProcessingStage",
    "ResourceSnapshot",
    "ProgressSnapshot",
    "ProcessingIssue",
    "ProcessingReport",
    "OptimizationMetrics",
    "RepositoryProcessingResult",
]
