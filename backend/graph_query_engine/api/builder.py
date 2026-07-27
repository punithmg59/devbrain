"""
Public Query API Builder.

Fluent immutable builder for constructing QueryRequest instances for the Public Query API.
"""

from typing import Any, Dict, Optional
from graph_query_engine.api.context import QueryContext
from graph_query_engine.api.options import QueryOptions
from graph_query_engine.api.request import QueryRequest


class ApiQueryBuilder:
    """
    Fluent immutable builder for Public Query API requests.
    Every mutation method returns a new builder instance.
    """

    def __init__(
        self,
        operation: str = "lookup_node",
        target: str = "",
        context: Optional[QueryContext] = None,
        options: Optional[QueryOptions] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._operation = operation
        self._target = target
        self._context = context or QueryContext()
        self._options = options or QueryOptions()
        self._parameters = parameters or {}

    def operation(self, op: str) -> "ApiQueryBuilder":
        """Returns a new builder with updated operation name."""
        return ApiQueryBuilder(
            operation=op,
            target=self._target,
            context=self._context,
            options=self._options,
            parameters=dict(self._parameters),
        )

    def target(self, tgt: str) -> "ApiQueryBuilder":
        """Returns a new builder with updated target."""
        return ApiQueryBuilder(
            operation=self._operation,
            target=tgt,
            context=self._context,
            options=self._options,
            parameters=dict(self._parameters),
        )

    def parameter(self, key: str, value: Any) -> "ApiQueryBuilder":
        """Returns a new builder with an added argument parameter."""
        new_params = dict(self._parameters)
        new_params[key] = value
        return ApiQueryBuilder(
            operation=self._operation,
            target=self._target,
            context=self._context,
            options=self._options,
            parameters=new_params,
        )

    def context(self, ctx: QueryContext) -> "ApiQueryBuilder":
        """Returns a new builder with updated QueryContext."""
        return ApiQueryBuilder(
            operation=self._operation,
            target=self._target,
            context=ctx,
            options=self._options,
            parameters=dict(self._parameters),
        )

    def options(self, opts: QueryOptions) -> "ApiQueryBuilder":
        """Returns a new builder with updated QueryOptions."""
        return ApiQueryBuilder(
            operation=self._operation,
            target=self._target,
            context=self._context,
            options=opts,
            parameters=dict(self._parameters),
        )

    def build(self) -> QueryRequest:
        """Constructs and returns the immutable QueryRequest."""
        return QueryRequest(
            operation=self._operation,
            target=self._target,
            parameters=self._parameters,
            context=self._context,
            options=self._options,
        )


__all__ = ["ApiQueryBuilder"]
