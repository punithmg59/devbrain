"""
Public Query API Session Management.

Manages query session context, state persistence, execution history, and default configuration.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.executor import QueryExecutor
from graph_query_engine.api.request import QueryRequest
from graph_query_engine.api.response import QueryResponse


class QuerySessionModel(BaseModel):
    """Immutable state model representing a QuerySession."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(
        default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}",
        description="Unique session ID",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation UTC timestamp",
    )
    default_context: QueryContext = Field(default_factory=QueryContext, description="Session default QueryContext")
    query_history: List[str] = Field(default_factory=list, description="Ordered list of executed request IDs")


class QuerySession:
    """
    Active Query Session facade.
    Wraps QueryExecutor with default QueryContext and history tracking.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        default_context: Optional[QueryContext] = None,
        executor: Optional[QueryExecutor] = None,
    ) -> None:
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.created_at = datetime.now(timezone.utc)
        self.default_context = default_context or QueryContext()
        self.executor = executor or QueryExecutor()
        self.history: List[QueryResponse] = []

    def execute(
        self,
        request: QueryRequest,
        graph_view: Optional[Any] = None,
        index_layer: Optional[Any] = None,
    ) -> QueryResponse:
        """Executes a QueryRequest within the session."""
        effective_context = request.context
        if effective_context.repository_id == "default_repo" and self.default_context.repository_id != "default_repo":
            effective_context = self.default_context

        request_with_context = QueryRequest(
            request_id=request.request_id,
            operation=request.operation,
            target=request.target,
            parameters=request.parameters,
            context=effective_context,
            options=request.options,
        )

        response = self.executor.execute(request_with_context, graph_view=graph_view, index_layer=index_layer)
        self.history.append(response)
        return response

    def update_default_context(self, context: QueryContext) -> None:
        """Updates session default context."""
        self.default_context = context

    def get_history(self) -> List[QueryResponse]:
        """Returns session query execution history."""
        return list(self.history)

    def clear_history(self) -> None:
        """Clears session query history."""
        self.history.clear()


__all__ = ["QuerySessionModel", "QuerySession"]
