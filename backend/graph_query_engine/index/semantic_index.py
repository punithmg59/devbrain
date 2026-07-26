"""
SemanticIndex Base Class for Repository Semantic Indexes.
"""

from graph_query_engine.index.base import BaseIndex


class SemanticIndex(BaseIndex):
    """
    Immutable parent class for all repository semantic indexes in Graph Query Engine.
    """
    pass


__all__ = ["SemanticIndex"]
