"""
GraphAdapter for Transforming DependencyGraph into Immutable GraphView.
"""

from typing import Any
import uuid

from graph_query_engine.types import (
    EdgeId,
    FileId,
    LanguageId,
    NodeId,
    RelationshipType,
    RepositoryId,
    SnapshotId,
)
from graph_query_engine.view.builder import GraphViewBuilder
from graph_query_engine.view.edge_view import ImmutableEdgeView
from graph_query_engine.view.factory import GraphViewFactory
from graph_query_engine.view.graph_view import GraphView
from graph_query_engine.view.identity import GraphIdentity
from graph_query_engine.view.metadata import GraphMetadata
from graph_query_engine.view.node_view import ImmutableNodeView
from graph_query_engine.view.snapshot import GraphSnapshotInfo
from graph_query_engine.view.statistics import GraphStatistics


class GraphAdapter:
    """
    Pure read-only adapter transforming DevBrain DependencyGraph into an immutable GraphView.
    """

    @classmethod
    def adapt(cls, dependency_graph: Any) -> GraphView:
        """
        Transforms a DependencyGraph model into a validated, immutable GraphView instance.

        Does NOT mutate input dependency_graph or execute query operations.
        """
        builder = GraphViewBuilder()

        # Extract Repository ID and Snapshot ID
        repo_id_str = getattr(dependency_graph, "repository_id", "repo_unknown")
        repo_id = RepositoryId(repo_id_str)
        snap_id_str = f"snap_{uuid.uuid4().hex[:12]}"
        snapshot_id = SnapshotId(snap_id_str)

        graph_version = str(getattr(dependency_graph, "version", "1.0.0"))

        # 1. Build GraphIdentity & GraphMetadata
        identity = GraphIdentity(
            repository_id=repo_id,
            snapshot_id=snapshot_id,
            graph_version=graph_version,
            schema_version="1.0.0",
            language=LanguageId("python"),
        )
        metadata = GraphMetadata(identity=identity)
        builder.set_metadata(metadata)

        # 2. Build GraphSnapshotInfo
        snapshot_info = GraphSnapshotInfo(
            snapshot_id=snapshot_id,
            snapshot_version="1.0.0",
            graph_hash="",
            checksum="sha256_placeholder",
        )
        builder.set_snapshot(snapshot_info)

        # 3. Transform Canonical Symbols into ImmutableNodeViews
        canonical_symbols = getattr(dependency_graph, "canonical_symbols", None)
        if canonical_symbols is not None:
            symbols_list = getattr(canonical_symbols, "symbols", []) or getattr(canonical_symbols, "__iter__", lambda: [])()
            for sym in symbols_list:
                node_id_str = str(getattr(sym, "symbol_id", getattr(sym, "id", "")))
                name = str(getattr(sym, "display_name", getattr(sym, "name", node_id_str)))
                qual_name = str(getattr(sym, "canonical_string", getattr(sym, "qualified_name", name)))
                node_type = str(getattr(sym, "kind", getattr(sym, "symbol_type", "SYMBOL")))
                file_path = str(getattr(sym, "file_path", getattr(sym, "file", "")))

                node_view = ImmutableNodeView(
                    node_id=NodeId(node_id_str),
                    name=name,
                    qualified_name=qual_name,
                    node_type=node_type,
                    file=FileId(file_path),
                )
                builder.add_node(node_view)

        # 4. Transform Relationship Edges into ImmutableEdgeViews
        raw_edges = getattr(dependency_graph, "edges", [])
        for edge in raw_edges:
            edge_id_str = str(getattr(edge, "edge_id", getattr(edge, "id", f"edge_{uuid.uuid4().hex[:8]}")))
            src_str = str(getattr(edge, "source_id", getattr(edge, "source", "")))
            tgt_str = str(getattr(edge, "target_id", getattr(edge, "target", "")))
            kind_str = str(getattr(edge, "kind", getattr(edge, "relationship_type", "USES"))).upper()

            # Map edge kind to RelationshipType enum
            rel_type = RelationshipType.USES
            if hasattr(RelationshipType, kind_str):
                rel_type = RelationshipType[kind_str]

            edge_view = ImmutableEdgeView(
                edge_id=EdgeId(edge_id_str),
                source_node_id=NodeId(src_str),
                target_node_id=NodeId(tgt_str),
                relationship_type=rel_type,
            )
            builder.add_edge(edge_view)

        # 5. Build Statistics Model
        raw_stats = getattr(dependency_graph, "statistics", None)
        node_cnt = getattr(raw_stats, "node_count", len(builder._nodes)) if raw_stats else len(builder._nodes)
        edge_cnt = getattr(raw_stats, "edge_count", len(builder._edges)) if raw_stats else len(builder._edges)

        statistics = GraphStatistics(
            node_count=node_cnt,
            edge_count=edge_cnt,
        )
        builder.set_statistics(statistics)

        # 6. Validate and Factory Construct GraphView
        return GraphViewFactory.create_from_builder(builder)


__all__ = ["GraphAdapter"]
