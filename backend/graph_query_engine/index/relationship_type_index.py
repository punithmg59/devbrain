"""
RelationshipTypeIndex for Grouping Relationships by RelationshipType Enum.
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.relationship_base_index import RelationshipBaseIndex
from graph_query_engine.types import RelationshipType
from graph_query_engine.view.edge_view import ImmutableEdgeView


class RelationshipTypeIndex(RelationshipBaseIndex):
    """
    Immutable, thread-safe index grouping edges by RelationshipType enum.
    """
    type_map: Mapping[str, tuple[ImmutableEdgeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of RelationshipType name string -> tuple of ImmutableEdgeView",
    )

    def relationships(self, rel_type: RelationshipType | str) -> tuple[ImmutableEdgeView, ...]:
        """Returns tuple of ImmutableEdgeView instances matching rel_type."""
        key = rel_type.name if isinstance(rel_type, RelationshipType) else str(rel_type).upper()
        return self.type_map.get(key, ())

    def count(self, rel_type: RelationshipType | str) -> int:
        """Returns count of relationships matching rel_type."""
        return len(self.relationships(rel_type))

    def types(self) -> tuple[str, ...]:
        """Returns tuple of all indexed RelationshipType names."""
        return tuple(self.type_map.keys())

    def lookup(self, key: Any) -> Iterable[ImmutableEdgeView]:
        """IGraphView lookup contract implementation."""
        return self.relationships(str(key))


__all__ = ["RelationshipTypeIndex"]
