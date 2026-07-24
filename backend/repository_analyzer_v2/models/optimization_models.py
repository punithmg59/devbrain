"""
models/optimization_models.py
-----------------------------
Phase 4.8.4 — Language-Independent Optimization & Fault Tolerance Data Models.

Defines production-quality, type-safe Pydantic V2 data models representing
processing stages, resource snapshots, progress telemetry, processing issues,
execution reports, optimization metrics, and repository processing results.

Design Principles
-----------------
- **Language-Independent**: Generic across Python, TypeScript, Java, Go, C#, Rust.
- **Pydantic V2 Native**: Full validation with Field constraints, default values,
  and serialization utilities (`model_dump()`, `model_dump_json()`).
- **Fault-Tolerant Reporting**: Captures file-level failures and recovery actions.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProcessingStage(str, Enum):
    """Execution stages of the Repository Analyzer pipeline."""
    DISCOVERY = "discovery"
    PARSING = "parsing"
    SEMANTIC_EXTRACTION = "semantic_extraction"
    SYMBOL_TABLE = "symbol_table"
    SCOPE_RESOLUTION = "scope_resolution"
    IMPORT_RESOLUTION = "import_resolution"
    REFERENCE_RESOLUTION = "reference_resolution"
    CALL_DETECTION = "call_detection"
    CALL_GRAPH_BUILDING = "call_graph_building"
    GRAPH_INDEXING = "graph_indexing"
    VALIDATION = "validation"
    COMPLETED = "completed"


class ResourceSnapshot(BaseModel):
    """Snapshot of process RSS memory footprint, CPU, and object counts at a point in time."""
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of snapshot")
    memory_rss_mb: float = Field(default=0.0, ge=0.0, description="Current process RSS memory in megabytes")
    peak_memory_mb: float = Field(default=0.0, ge=0.0, description="Peak process RSS memory in megabytes")
    cpu_percent: float = Field(default=0.0, ge=0.0, description="Current process CPU utilization percentage")
    active_stage: ProcessingStage = Field(default=ProcessingStage.DISCOVERY, description="Current active pipeline stage")
    files_processed: int = Field(default=0, ge=0, description="Total source files processed so far")
    nodes_processed: int = Field(default=0, ge=0, description="Total graph nodes created so far")
    edges_processed: int = Field(default=0, ge=0, description="Total graph edges created so far")


class ProgressSnapshot(BaseModel):
    """Report-only snapshot of current processing progress, completed stages, and ETA."""
    stage: ProcessingStage = Field(default=ProcessingStage.DISCOVERY, description="Current active stage")
    completed_stages: List[ProcessingStage] = Field(default_factory=list, description="List of completed stages")
    total_stages: int = Field(default=12, ge=1, description="Total pipeline stages count")
    files_completed: int = Field(default=0, ge=0, description="Files completed so far")
    total_files: int = Field(default=0, ge=0, description="Total repository files")
    percentage_complete: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of pipeline work complete")
    estimated_remaining_sec: float = Field(default=0.0, ge=0.0, description="Estimated remaining duration in seconds")
    current_operation: str = Field(default="", description="Human-readable description of current operation")


class ProcessingIssue(BaseModel):
    """Individual issue or recoverable failure recorded during repository processing."""
    issue_id: str = Field(
        default_factory=lambda: f"procissue-{uuid.uuid4().hex[:12]}",
        description="Unique issue identifier",
    )
    severity: str = Field(default="error", description="'info', 'warning', 'error', 'critical'")
    stage: ProcessingStage = Field(..., description="Pipeline stage where issue occurred")
    file_path: Optional[str] = Field(default=None, description="Associated source file path if applicable")
    reason: str = Field(..., description="Human-readable explanation of error or issue")
    exception_class: Optional[str] = Field(default=None, description="Exception class name if caught from code")
    recovery_action: str = Field(default="skipped_file_and_continued", description="Action taken by fault tolerance engine")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of issue occurrence")


class ProcessingReport(BaseModel):
    """Aggregated processing summary report for repository optimization."""
    total_files_processed: int = Field(default=0, ge=0, description="Total files successfully processed")
    files_failed: int = Field(default=0, ge=0, description="Total files that encountered recoverable failures")
    files_skipped: int = Field(default=0, ge=0, description="Total files skipped during processing")
    nodes_processed: int = Field(default=0, ge=0, description="Total nodes generated")
    edges_processed: int = Field(default=0, ge=0, description="Total edges generated")
    issues: List[ProcessingIssue] = Field(default_factory=list, description="List of recorded ProcessingIssue objects")
    error_count: int = Field(default=0, ge=0, description="Total error count")
    warning_count: int = Field(default=0, ge=0, description="Total warning count")
    recovery_count: int = Field(default=0, ge=0, description="Total successful fault tolerance recovery actions")


class OptimizationMetrics(BaseModel):
    """Performance telemetry and scalability metrics for large repository optimization."""
    processing_duration_ms: float = Field(default=0.0, ge=0.0, description="Total processing duration in milliseconds")
    files_processed: int = Field(default=0, ge=0, description="Total files processed")
    files_skipped: int = Field(default=0, ge=0, description="Total files skipped")
    files_failed: int = Field(default=0, ge=0, description="Total files failed")
    nodes_processed: int = Field(default=0, ge=0, description="Total nodes processed")
    edges_processed: int = Field(default=0, ge=0, description="Total edges processed")
    peak_memory_mb: float = Field(default=0.0, ge=0.0, description="Peak memory footprint in megabytes")
    average_batch_size: float = Field(default=0.0, ge=0.0, description="Average processing batch size")
    recovery_count: int = Field(default=0, ge=0, description="Total fault-tolerant recoveries executed")
    warnings_count: int = Field(default=0, ge=0, description="Total warnings recorded")
    errors_count: int = Field(default=0, ge=0, description="Total errors recorded")


class RepositoryProcessingResult(BaseModel):
    """Container returned by RepositoryProcessingPipeline execution."""
    result_id: str = Field(
        default_factory=lambda: f"piperes-{uuid.uuid4().hex[:12]}",
        description="Unique processing result ID",
    )
    repository_id: str = Field(default="repo", description="Repository identifier")
    success: bool = Field(default=True, description="True if pipeline completed without unrecoverable failures")
    completed_stages: List[ProcessingStage] = Field(default_factory=list, description="List of completed stages")
    processing_report: ProcessingReport = Field(default_factory=ProcessingReport, description="Processing report container")
    metrics: OptimizationMetrics = Field(default_factory=OptimizationMetrics, description="Scalability and optimization telemetry metrics")
    resource_snapshot: ResourceSnapshot = Field(default_factory=ResourceSnapshot, description="Final resource footprint snapshot")
    warnings: List[str] = Field(default_factory=list, description="List of human-readable warnings")
    errors: List[str] = Field(default_factory=list, description="List of human-readable errors")
