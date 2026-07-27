"""
Public Query API Request Specification.

Represents an incoming high-level query request to the Public Query API facade.
"""

import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.options import QueryOptions


class QueryRequest(BaseModel):
    """
    Immutable Public Query API Request model.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}",
        description="Unique request trace ID",
    )
    operation: str = Field(..., description="High-level engineering operation name")
    target: str = Field(default="", description="Primary target symbol, entity ID, path, or pattern")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation-specific argument parameter dictionary")
    context: QueryContext = Field(default_factory=QueryContext, description="Query scope and runtime context")
    options: QueryOptions = Field(default_factory=QueryOptions, description="Execution options container")


__all__ = ["QueryRequest"]
