"""
LookupIndex Base Class for Core Lookup Indexes.
"""

from graph_query_engine.index.base import BaseIndex


class LookupIndex(BaseIndex):
    """
    Immutable parent class for all core key-value lookup indexes in Graph Query Engine.
    """
    pass


__all__ = ["LookupIndex"]
