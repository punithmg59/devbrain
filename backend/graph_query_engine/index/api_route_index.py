"""
APIRouteIndex for Indexing Repository API Endpoint Routes (HTTP Method, Route Path, Handlers).
"""

from typing import Any, Iterable, Mapping, Optional
from pydantic import BaseModel, ConfigDict, Field

from graph_query_engine.errors import IndexLookupError
from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.types import NodeId
from graph_query_engine.view.node_view import ImmutableNodeView


class APIRouteRecord(BaseModel):
    """
    Immutable representation of an indexed API route endpoint.
    """
    model_config = ConfigDict(frozen=True)

    http_method: str = Field(..., description="HTTP Method (GET, POST, PUT, DELETE, etc.)")
    route_path: str = Field(..., description="API Route URL path template (e.g. /users)")
    handler_node: ImmutableNodeView = Field(..., description="Handler function/controller ImmutableNodeView")
    controller_name: str = Field(default="", description="Controller/service class name")
    decorators: tuple[str, ...] = Field(default_factory=tuple, description="Route decorator strings")


class APIRouteIndex(SemanticIndex):
    """
    Immutable, thread-safe index mapping HTTP routes (method + path) to API handlers.
    """
    route_map: Mapping[str, APIRouteRecord] = Field(
        default_factory=dict,
        description="Immutable mapping of 'METHOD:PATH' -> APIRouteRecord",
    )

    def contains(self, http_method: str, route_path: str) -> bool:
        """Returns True if HTTP method and route_path endpoint exists."""
        key = f"{http_method.upper()}:{route_path}"
        return key in self.route_map

    def get(self, http_method: str, route_path: str) -> APIRouteRecord:
        """
        Retrieves APIRouteRecord by HTTP method and route_path. Raises IndexLookupError if missing.
        """
        key = f"{http_method.upper()}:{route_path}"
        route = self.route_map.get(key)
        if route is None:
            raise IndexLookupError(f"API Route '{key}' not found in APIRouteIndex.")
        return route

    def try_get(self, http_method: str, route_path: str) -> Optional[APIRouteRecord]:
        """Retrieves APIRouteRecord by HTTP method and route_path or returns None."""
        key = f"{http_method.upper()}:{route_path}"
        return self.route_map.get(key)

    def routes(self) -> tuple[APIRouteRecord, ...]:
        """Returns tuple of all indexed API routes."""
        return tuple(self.route_map.values())

    def count(self) -> int:
        """Returns total number of indexed API routes."""
        return len(self.route_map)

    def lookup(self, key: Any) -> Iterable[APIRouteRecord]:
        """IGraphView lookup contract implementation."""
        res = self.route_map.get(str(key))
        return (res,) if res is not None else ()


__all__ = [
    "APIRouteRecord",
    "APIRouteIndex",
]
