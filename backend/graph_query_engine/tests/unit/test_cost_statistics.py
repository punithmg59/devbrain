"""
Unit test suite for GraphStatisticsMetadata models.
"""

from graph_query_engine.cost import (
    EdgeStatistics,
    GraphStatisticsMetadata,
    NodeStatistics,
)


def test_graph_statistics_metadata_defaults():
    stats = GraphStatisticsMetadata()
    assert stats.nodes.total_node_count == 10_000
    assert stats.edges.total_edge_count == 50_000
    assert stats.edges.average_degree == 5.0
    assert "PRIMARY_NODE" in stats.indexes.available_indexes
