"""
Execution Plan Representation Models.

Immutable root plan object describing HOW the runtime will execute the query.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.cost import CostEstimate
from graph_query_engine.execution.diagnostics import ExecutionPlannerDiagnosticItem
from graph_query_engine.execution.pipeline import ExecutionPipeline, StageDependencyGraph
from graph_query_engine.execution.stage import ExecutionStage
from graph_query_engine.execution.version import ExecutionPlanVersion
from graph_query_engine.types import QueryId


class ExecutionMetadata(BaseModel):
    """
    Immutable execution runtime configuration and metadata container.
    """
    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    timeout_ms: int = Field(default=30_000, ge=0, description="Query execution timeout in milliseconds")
    max_memory_bytes: int = Field(default=512 * 1024 * 1024, ge=0, description="Memory allocation limit in bytes")
    checkpoint_enabled: bool = Field(default=False, description="True if runtime state checkpointing is enabled")
    cancellation_token_id: str = Field(
        default_factory=lambda: f"cancel_{uuid.uuid4().hex[:8]}",
        description="Cancellation token handle string",
    )
    progress_tracking_id: str = Field(
        default_factory=lambda: f"prog_{uuid.uuid4().hex[:8]}",
        description="Progress tracking handle string",
    )


class ExecutionPlan(BaseModel):
    """
    Canonical immutable ExecutionPlan root model produced by ExecutionPlanner.
    """
    model_config = ConfigDict(frozen=True)

    execution_plan_id: str = Field(
        default_factory=lambda: f"eplan_{uuid.uuid4().hex[:12]}",
        description="Unique ExecutionPlan identifier string",
    )
    physical_plan_id: str = Field(..., description="Associated input PhysicalPlan plan_id")
    query_id: QueryId = Field(..., description="Associated source QueryId")
    version: ExecutionPlanVersion = Field(default_factory=ExecutionPlanVersion, description="Execution plan version model")
    metadata: ExecutionMetadata = Field(default_factory=ExecutionMetadata, description="Runtime execution metadata")
    stages: Tuple[ExecutionStage, ...] = Field(default_factory=tuple, description="Tuple of execution stages")
    dependency_graph: StageDependencyGraph = Field(default_factory=StageDependencyGraph, description="Stage dependency graph")
    pipeline: ExecutionPipeline = Field(..., description="Ordered execution pipeline container")
    estimated_runtime_ms: float = Field(default=0.0, ge=0.0, description="Estimated total execution runtime in milliseconds")
    diagnostics: Tuple[ExecutionPlannerDiagnosticItem, ...] = Field(default_factory=tuple, description="Execution planner diagnostics log")

    def accept(self, visitor: Any) -> Any:
        """Visits this ExecutionPlan container."""
        return visitor.visit_execution_plan(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes ExecutionPlan to python dict."""
        return self.model_dump(mode="python")


__all__ = [
    "ExecutionMetadata",
    "ExecutionPlan",
]
