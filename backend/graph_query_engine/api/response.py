"""
Public Query API Response Specification.

Outer response model returned by the Public Query API facade.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.api.errors import QueryErrorDetail
from graph_query_engine.api.result import QueryDiagnostics, QueryResult, QueryStatistics


class ResponseStatus(str, Enum):
    """Enumeration of QueryResponse status values."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class QueryResponse(BaseModel):
    """
    Canonical immutable Public Query API response model.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(..., description="Associated QueryRequest request_id")
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS, description="Query outcome status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Completion timestamp in UTC",
    )
    result: QueryResult = Field(default_factory=QueryResult, description="Engineering query result container")
    statistics: QueryStatistics = Field(default_factory=QueryStatistics, description="Execution performance statistics")
    diagnostics: QueryDiagnostics = Field(default_factory=QueryDiagnostics, description="Diagnostic logs and summary")
    error: Optional[QueryErrorDetail] = Field(default=None, description="Error detail if status is FAILED or PARTIAL")


__all__ = ["ResponseStatus", "QueryResponse"]
