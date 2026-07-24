"""
analysis/optimization/optimization_models.py
---------------------------------------------
Phase 4.8.4 — Package Internal Models Re-export.

Re-exports optimization models from models.optimization_models.
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

__all__ = [
    "ProcessingStage",
    "ResourceSnapshot",
    "ProgressSnapshot",
    "ProcessingIssue",
    "ProcessingReport",
    "OptimizationMetrics",
    "RepositoryProcessingResult",
]
