"""
RelationshipBaseIndex Base Class for Relationship Adjacency Indexes.
"""

from graph_query_engine.index.base import BaseIndex


class RelationshipBaseIndex(BaseIndex):
    """
    Immutable parent class for all relationship adjacency indexes in Graph Query Engine.
    """
    pass


__all__ = ["RelationshipBaseIndex"]
