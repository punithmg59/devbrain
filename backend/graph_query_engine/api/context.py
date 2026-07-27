"""
Public Query Context Representation Model.

Encapsulates execution context parameters including repository scope, version, filters, limits, and runtime flags.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class QueryContext(BaseModel):
    """
    Immutable QueryContext model for configuring engine query requests.
    """

    model_config = ConfigDict(frozen=True)

    repository_id: str = Field(default="default_repo", description="Target repository ID")
    branch: Optional[str] = Field(default="main", description="Target repository branch name")
    commit: Optional[str] = Field(default=None, description="Target repository commit SHA")
    language: Optional[str] = Field(default=None, description="Scope language filter")
    scope: Optional[str] = Field(default=None, description="Package or module scope constraint")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary property filter dictionary")
    depth_limit: int = Field(default=10, description="Maximum graph traversal depth limit")
    max_nodes_limit: int = Field(default=5000, description="Maximum total nodes to visit or return")
    timeout_seconds: float = Field(default=30.0, description="Query execution timeout limit in seconds")
    cancellation_token: Optional[str] = Field(default=None, description="Cancellation handle string")
    execution_options: Dict[str, Any] = Field(default_factory=dict, description="Custom execution engine flags")

    def with_repository(self, repository_id: str, branch: Optional[str] = None, commit: Optional[str] = None) -> "QueryContext":
        """Returns a new QueryContext with updated repository information."""
        return QueryContext(
            repository_id=repository_id,
            branch=branch or self.branch,
            commit=commit or self.commit,
            language=self.language,
            scope=self.scope,
            filters=dict(self.filters),
            depth_limit=self.depth_limit,
            max_nodes_limit=self.max_nodes_limit,
            timeout_seconds=self.timeout_seconds,
            cancellation_token=self.cancellation_token,
            execution_options=dict(self.execution_options),
        )

    def with_limits(self, depth_limit: Optional[int] = None, max_nodes_limit: Optional[int] = None, timeout_seconds: Optional[float] = None) -> "QueryContext":
        """Returns a new QueryContext with updated limit constraints."""
        return QueryContext(
            repository_id=self.repository_id,
            branch=self.branch,
            commit=self.commit,
            language=self.language,
            scope=self.scope,
            filters=dict(self.filters),
            depth_limit=depth_limit if depth_limit is not None else self.depth_limit,
            max_nodes_limit=max_nodes_limit if max_nodes_limit is not None else self.max_nodes_limit,
            timeout_seconds=timeout_seconds if timeout_seconds is not None else self.timeout_seconds,
            cancellation_token=self.cancellation_token,
            execution_options=dict(self.execution_options),
        )


__all__ = ["QueryContext"]
