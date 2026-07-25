"""
tests/test_core_edges.py
-------------------------
Comprehensive unit test suite for Step 4.1 Primary Edge Domain Model & EdgeCollection.
"""

from typing import Dict
import pytest
from pydantic import ValidationError

from core.edges import (
    EDGE_COLLECTION_VERSION,
    Edge,
    EdgeAttributes,
    EdgeCollection,
    EdgeDirection,
    EdgeEvidence,
    EdgeID,
    EdgeKind,
    EdgeMetadata,
    EdgeStatistics,
    EdgeStrength,
    EdgeValidator,
    dict_to_edge_collection,
    edge_collection_to_dict,
    edge_collection_to_json,
    generate_edge_id,
    hash_edge_collection,
    json_to_edge_collection,
)
from core.symbols import Language, SymbolID


class TestEdgeDomainModel:
    def test_edge_creation_and_fields(self):
        source_id = SymbolID(value="sym_111111111111111111111111")
        target_id = SymbolID(value="sym_222222222222222222222222")

        eid = generate_edge_id("repo-1", source_id, target_id, EdgeKind.IMPORT)

        edge = Edge(
            id=eid,
            source_symbol_id=source_id,
            target_symbol_id=target_id,
            kind=EdgeKind.IMPORT,
            direction=EdgeDirection.DIRECTED,
            strength=EdgeStrength.STRONG,
            confidence=1.0,
            language=Language.PYTHON,
            repository_id="repo-1",
            file_path="app/main.py",
            evidence=EdgeEvidence(stage_name="Step 4.2", explanation="Module import statement"),
            metadata=EdgeMetadata(plugin={"plugin_name": "python-builder"})
        )

        assert edge.id.value.startswith("edge_")
        assert edge.kind == EdgeKind.IMPORT
        assert edge.direction == EdgeDirection.DIRECTED
        assert edge.strength == EdgeStrength.STRONG
        assert edge.metadata.plugin["plugin_name"] == "python-builder"

    def test_edge_immutability(self):
        source_id = SymbolID(value="sym_111111111111111111111111")
        target_id = SymbolID(value="sym_222222222222222222222222")
        eid = generate_edge_id("repo-1", source_id, target_id, EdgeKind.CALL)

        edge = Edge(
            id=eid,
            source_symbol_id=source_id,
            target_symbol_id=target_id,
            kind=EdgeKind.CALL,
            language=Language.PYTHON,
            repository_id="repo-1"
        )

        with pytest.raises(ValidationError):
            edge.confidence = 0.5  # type: ignore


class TestEdgeIDAlgorithm:
    def test_deterministic_edge_id_generation(self):
        s = SymbolID(value="sym_111111111111111111111111")
        t = SymbolID(value="sym_222222222222222222222222")

        id1 = generate_edge_id("repo-abc", s, t, EdgeKind.CALL)
        id2 = generate_edge_id("repo-abc", "sym_111111111111111111111111", "sym_222222222222222222222222", "call")

        assert id1 == id2
        assert id1.value.startswith("edge_")

    def test_discriminator_alters_edge_id(self):
        s = SymbolID(value="sym_111111111111111111111111")
        t = SymbolID(value="sym_222222222222222222222222")

        id1 = generate_edge_id("repo-abc", s, t, EdgeKind.CALL)
        id2 = generate_edge_id("repo-abc", s, t, EdgeKind.CALL, discriminator="call_site_line_10")

        assert id1 != id2


class TestEdgeKindsAndEnums:
    def test_all_22_minimum_required_edge_kinds_supported(self):
        expected_kinds = [
            "import", "call", "inheritance", "implementation", "override",
            "reference", "type_reference", "return_type", "parameter_type",
            "field_type", "throws", "decorator", "annotation", "composition",
            "aggregation", "containment", "dependency", "configuration",
            "framework", "plugin", "generated", "future", "unknown"
        ]

        for k_str in expected_kinds:
            enum_val = EdgeKind(k_str)
            assert enum_val.value == k_str


class TestEdgeCollection:
    def create_sample_edge_collection(self) -> EdgeCollection:
        s1 = SymbolID(value="sym_111111111111111111111111")
        t1 = SymbolID(value="sym_222222222222222222222222")
        t2 = SymbolID(value="sym_333333333333333333333333")

        e1 = Edge(
            id=generate_edge_id("repo-1", s1, t1, EdgeKind.IMPORT),
            source_symbol_id=s1,
            target_symbol_id=t1,
            kind=EdgeKind.IMPORT,
            language=Language.PYTHON,
            repository_id="repo-1",
            file_path="app/main.py"
        )

        e2 = Edge(
            id=generate_edge_id("repo-1", s1, t2, EdgeKind.CALL),
            source_symbol_id=s1,
            target_symbol_id=t2,
            kind=EdgeKind.CALL,
            language=Language.PYTHON,
            repository_id="repo-1",
            file_path="app/main.py"
        )

        by_id: Dict[EdgeID, Edge] = {e1.id: e1, e2.id: e2}
        by_src: Dict[SymbolID, list[EdgeID]] = {s1: [e1.id, e2.id]}
        by_tgt: Dict[SymbolID, list[EdgeID]] = {t1: [e1.id], t2: [e2.id]}
        by_kind: Dict[EdgeKind, list[EdgeID]] = {EdgeKind.IMPORT: [e1.id], EdgeKind.CALL: [e2.id]}

        return EdgeCollection(
            repository_id="repo-1",
            edges=[e1, e2],
            edges_by_id=by_id,
            edges_by_source=by_src,
            edges_by_target=by_tgt,
            edges_by_kind=by_kind,
            statistics=EdgeStatistics(total_edges=2)
        )

    def test_edge_collection_lookups(self):
        coll = self.create_sample_edge_collection()

        # Outgoing lookup
        out_edges = coll.get_outgoing_edges("sym_111111111111111111111111")
        assert len(out_edges) == 2

        # Incoming lookup
        in_edges = coll.get_incoming_edges("sym_222222222222222222222222")
        assert len(in_edges) == 1
        assert in_edges[0].kind == EdgeKind.IMPORT

        # Kind lookup
        call_edges = coll.get_edges_by_kind(EdgeKind.CALL)
        assert len(call_edges) == 1
        assert call_edges[0].target_symbol_id.value == "sym_333333333333333333333333"


class TestSerialization:
    def test_json_roundtrip(self):
        coll = TestEdgeCollection().create_sample_edge_collection()

        json_str = edge_collection_to_json(coll, indent=True)
        assert "_schema_version" in json_str

        reconstructed = json_to_edge_collection(json_str, EdgeCollection)
        assert reconstructed.repository_id == coll.repository_id
        assert len(reconstructed.edges) == len(coll.edges)

    def test_dict_roundtrip(self):
        coll = TestEdgeCollection().create_sample_edge_collection()

        d = edge_collection_to_dict(coll)
        reconstructed = dict_to_edge_collection(d, EdgeCollection)
        assert reconstructed == coll

    def test_hash_edge_collection(self):
        coll = TestEdgeCollection().create_sample_edge_collection()

        h1 = hash_edge_collection(coll)
        h2 = hash_edge_collection(coll)
        assert h1 == h2
        assert len(h1) == 64
