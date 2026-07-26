"""
AnnotationIndex for Grouping Decorators and Annotations (@app.get, @dataclass, @Controller, etc.).
"""

from typing import Any, Iterable, Mapping
from pydantic import Field

from graph_query_engine.index.semantic_index import SemanticIndex
from graph_query_engine.view.node_view import ImmutableNodeView


class AnnotationIndex(SemanticIndex):
    """
    Immutable, thread-safe index grouping symbols by decorator/annotation string.
    """
    annotation_map: Mapping[str, tuple[ImmutableNodeView, ...]] = Field(
        default_factory=dict,
        description="Immutable mapping of annotation string -> tuple of ImmutableNodeViews",
    )

    def by_annotation(self, annotation: str) -> tuple[ImmutableNodeView, ...]:
        """Returns tuple of nodes decorated with annotation."""
        clean_ann = annotation.strip()
        if not clean_ann.startswith("@"):
            clean_ann = f"@{clean_ann}"
        return self.annotation_map.get(clean_ann, ())

    def annotations(self) -> tuple[str, ...]:
        """Returns tuple of all indexed annotation strings."""
        return tuple(self.annotation_map.keys())

    def count(self, annotation: str) -> int:
        """Returns count of nodes decorated with annotation."""
        return len(self.by_annotation(annotation))

    def lookup(self, key: Any) -> Iterable[ImmutableNodeView]:
        """IGraphView lookup contract implementation."""
        return self.by_annotation(str(key))


__all__ = ["AnnotationIndex"]
