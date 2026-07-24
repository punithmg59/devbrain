"""
analysis/optimization/optimization_config.py
---------------------------------------------
Phase 4.8.4 — Optimization & Fault Tolerance Configuration.

Defines production-grade settings for batch processing, memory thresholds,
progress update intervals, fault tolerance flags, and error limits.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OptimizationConfig(BaseModel):
    """Configuration container controlling large repository optimization and fault tolerance."""
    batch_size: int = Field(
        default=500,
        ge=1,
        description="Number of files to process per processing batch",
    )
    max_memory_threshold_mb: float = Field(
        default=4096.0,
        ge=256.0,
        description="Process RSS memory threshold in MB before triggering memory cleanup / GC",
    )
    progress_update_interval_sec: float = Field(
        default=1.0,
        ge=0.1,
        description="Time interval in seconds between progress snapshot updates",
    )
    logging_interval_sec: float = Field(
        default=5.0,
        ge=0.5,
        description="Time interval in seconds between structured telemetry log entries",
    )
    continue_on_error: bool = Field(
        default=True,
        description="If True, file-level recoverable failures log issue and continue processing remaining files",
    )
    max_collected_errors: int = Field(
        default=1000,
        ge=1,
        description="Maximum number of recoverable error issues to collect before suppressing logs",
    )
    max_warning_count: int = Field(
        default=5000,
        ge=1,
        description="Maximum number of warning issues to collect",
    )
    enable_streaming: bool = Field(
        default=True,
        description="If True, processes files in streaming batches using generator iterators",
    )
    enable_memory_cleanup: bool = Field(
        default=True,
        description="If True, explicitly releases intermediate data structures between pipeline stages",
    )
