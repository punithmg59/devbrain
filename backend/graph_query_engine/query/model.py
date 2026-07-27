"""
Root EngineeringQuery Representation Model.

The canonical root representation of every engineering query in DevBrain.
100% Immutable, language-neutral, and strongly typed.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.query.ast import QueryAST
from graph_query_engine.query.constraints import QueryConstraints
from graph_query_engine.query.diagnostics import QueryDiagnosticsMetadata
from graph_query_engine.query.result import ResultSpecification
from graph_query_engine.query.version import QueryVersion
from graph_query_engine.types import CorrelationId, QueryId, RequestId


class SourceInfo(BaseModel):
    """Immutable caller and request source metadata."""
    model_config = ConfigDict(frozen=True)

    caller_id: str = Field(default="system", description="Identifier of calling client or component")
    request_id: RequestId = Field(
        default_factory=lambda: RequestId(f"req_{uuid.uuid4().hex[:12]}"),
        description="Unique request trace ID",
    )
    correlation_id: CorrelationId = Field(
        default_factory=lambda: CorrelationId(f"corr_{uuid.uuid4().hex[:12]}"),
        description="Correlation ID for distributed tracing",
    )
    origin_system: str = Field(default="devbrain_analyzer", description="Originating subsystem name")


class QueryOptions(BaseModel):
    """Immutable query execution behavior options."""
    model_config = ConfigDict(frozen=True)

    enable_cache: bool = Field(default=True, description="Allow cached results if available")
    timeout_seconds: float = Field(default=30.0, gt=0.0, description="Query execution timeout seconds")
    strict_validation: bool = Field(default=True, description="Fail query construction on non-fatal warnings")
    custom_flags: Dict[str, Any] = Field(default_factory=dict, description="Custom query behavior flags")


class PlannerQueryOptions(BaseModel):
    """Immutable planner hint options."""
    model_config = ConfigDict(frozen=True)

    optimization_level: int = Field(default=2, ge=0, le=3, description="Optimization level (0=none, 3=aggressive)")
    enable_cost_model: bool = Field(default=True, description="Use cost estimation during planning")
    max_planning_time_ms: float = Field(default=5000.0, gt=0.0, description="Max planning phase duration")
    planner_hints: Tuple[str, ...] = Field(default_factory=tuple, description="Explicit planner hint strings")


class QueryMetadata(BaseModel):
    """Immutable query metadata tags and descriptive annotations."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(default="EngineeringQuery", description="Human readable query name")
    description: str = Field(default="", description="Query intent description string")
    owner: str = Field(default="devbrain", description="Query author or owning subsystem")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    tags: Tuple[str, ...] = Field(default_factory=tuple, description="Query classification tags")


class EngineeringQuery(BaseModel):
    """
    Root immutable representation of an engineering query in DevBrain.

    Contains AST, constraints, result specification, source metadata,
    diagnostics context, versioning, and options.
    """
    model_config = ConfigDict(frozen=True)

    query_id: QueryId = Field(
        default_factory=lambda: QueryId(f"qry_{uuid.uuid4().hex[:12]}"),
        description="Unique EngineeringQuery identifier",
    )
    version: QueryVersion = Field(default_factory=QueryVersion, description="Schema and AST versioning model")
    metadata: QueryMetadata = Field(default_factory=QueryMetadata, description="Query metadata annotations")
    options: QueryOptions = Field(default_factory=QueryOptions, description="Query execution behavior options")
    planner_options: PlannerQueryOptions = Field(default_factory=PlannerQueryOptions, description="Planner hint options")
    source_info: SourceInfo = Field(default_factory=SourceInfo, description="Request source metadata")
    diagnostics: QueryDiagnosticsMetadata = Field(default_factory=QueryDiagnosticsMetadata, description="Diagnostics metadata")
    constraints: QueryConstraints = Field(default_factory=QueryConstraints, description="Resource limit constraints")
    result_spec: ResultSpecification = Field(default_factory=ResultSpecification, description="Desired result spec")
    ast: QueryAST = Field(..., description="Query AST tree representation")

    def accept(self, visitor: Any) -> Any:
        """Dispatches visitor to EngineeringQuery."""
        return visitor.visit_query(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes EngineeringQuery into plain python dict."""
        return self.model_dump(mode="python")


__all__ = [
    "SourceInfo",
    "QueryOptions",
    "PlannerQueryOptions",
    "QueryMetadata",
    "EngineeringQuery",
]
