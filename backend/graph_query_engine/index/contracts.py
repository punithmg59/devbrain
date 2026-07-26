"""
Index Infrastructure Protocol Contracts Re-export.
"""

from graph_query_engine.contracts.index import (
    IIndex,
    IIndexBuilder,
    IIndexDescriptor,
    IIndexFactory,
    IIndexLifecycle,
    IIndexMetadata,
    IIndexProvider,
    IIndexRegistry,
    IIndexStatistics,
    IIndexValidator,
)

__all__ = [
    "IIndex",
    "IIndexBuilder",
    "IIndexRegistry",
    "IIndexFactory",
    "IIndexLifecycle",
    "IIndexStatistics",
    "IIndexValidator",
    "IIndexMetadata",
    "IIndexDescriptor",
    "IIndexProvider",
]
