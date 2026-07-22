"""
tests/test_ast_models.py
-------------------------
Comprehensive unit tests for Phase 3.2 — AST Data Models.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from models.ast import (
    ASTNode,
    ASTRoot,
    NodeLocation,
    NodeMetadata,
    NodeRange,
    NodeRelationship,
    NodeType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_range(start_line: int = 1, start_col: int = 0, end_line: int = 1, end_col: int = 10) -> NodeRange:
    return NodeRange(
        start=NodeLocation(line=start_line, column=start_col),
        end=NodeLocation(line=end_line, column=end_col),
        start_byte=0,
        end_byte=10,
    )


def make_node(
    type_: NodeType = NodeType.FUNCTION,
    name: str = "foo",
    start_line: int = 1,
    end_line: int = 5,
) -> ASTNode:
    return ASTNode(
        type=type_,
        name=name,
        range=NodeRange(
            start=NodeLocation(line=start_line, column=0),
            end=NodeLocation(line=end_line, column=10),
        ),
    )


# ---------------------------------------------------------------------------
# NodeType Enum Tests
# ---------------------------------------------------------------------------

def test_node_type_enum():
    assert NodeType.MODULE.value == "module"
    assert NodeType.FUNCTION.value == "function"
    assert NodeType.CLASS.value == "class"
    assert NodeType.IDENTIFIER.value == "identifier"


# ---------------------------------------------------------------------------
# NodeLocation & NodeRange Tests
# ---------------------------------------------------------------------------

def test_node_location_and_range_valid():
    loc1 = NodeLocation(line=1, column=0)
    loc2 = NodeLocation(line=2, column=5)
    r = NodeRange(start=loc1, end=loc2, start_byte=0, end_byte=100)
    assert r.start.line == 1
    assert r.end.line == 2


def test_node_range_invalid_ordering_raises():
    loc_start = NodeLocation(line=10, column=5)
    loc_end = NodeLocation(line=5, column=0)
    with pytest.raises(ValidationError, match="End line .* cannot precede start line"):
        NodeRange(start=loc_start, end=loc_end)

    # Same line, invalid column
    loc_s = NodeLocation(line=5, column=10)
    loc_e = NodeLocation(line=5, column=2)
    with pytest.raises(ValidationError, match="End column .* cannot precede start column"):
        NodeRange(start=loc_s, end=loc_e)


def test_node_range_invalid_byte_offsets_raises():
    with pytest.raises(ValidationError, match="end_byte .* cannot be less than start_byte"):
        NodeRange(
            start=NodeLocation(line=1, column=0),
            end=NodeLocation(line=1, column=10),
            start_byte=50,
            end_byte=10,
        )


# ---------------------------------------------------------------------------
# NodeMetadata & Relationship Tests
# ---------------------------------------------------------------------------

def test_node_metadata_defaults_and_custom():
    meta = NodeMetadata(docstring="Calculate total", modifiers=["public", "async"])
    assert meta.docstring == "Calculate total"
    assert meta.modifiers == ["public", "async"]
    assert meta.is_definition is False

    meta.custom["complexity"] = 5
    assert meta.custom["complexity"] == 5


def test_node_relationship_defaults():
    rel = NodeRelationship()
    assert rel.parent_id is None
    assert rel.children_ids == []
    assert rel.sibling_ids == []


# ---------------------------------------------------------------------------
# ASTNode & Hierarchy Linkage Tests
# ---------------------------------------------------------------------------

def test_ast_node_creation():
    node = make_node(NodeType.CLASS, "Calculator")
    assert node.node_id.startswith("ast-")
    assert node.type == NodeType.CLASS
    assert node.name == "Calculator"
    assert node.children == []


def test_ast_node_add_child_linkage():
    parent = make_node(NodeType.CLASS, "MyClass")
    child1 = make_node(NodeType.METHOD, "method_a")
    child2 = make_node(NodeType.METHOD, "method_b")

    parent.add_child(child1)
    parent.add_child(child2)

    assert len(parent.children) == 2
    assert parent.relationships.children_ids == [child1.node_id, child2.node_id]
    assert child1.relationships.parent_id == parent.node_id
    assert child2.relationships.parent_id == parent.node_id


def test_ast_node_traversal_walk():
    root = make_node(NodeType.MODULE, "main")
    fn1 = make_node(NodeType.FUNCTION, "fn1")
    fn2 = make_node(NodeType.FUNCTION, "fn2")
    param = make_node(NodeType.PARAMETER, "x")

    root.add_child(fn1)
    root.add_child(fn2)
    fn1.add_child(param)

    # Walk should yield root, fn1, param, fn2 (DFS order)
    walked_names = [n.name for n in root.walk()]
    assert walked_names == ["main", "fn1", "x", "fn2"]

    functions = root.find_by_type(NodeType.FUNCTION)
    assert len(functions) == 2
    assert [f.name for f in functions] == ["fn1", "fn2"]

    by_name = root.find_by_name("x")
    assert len(by_name) == 1
    assert by_name[0].type == NodeType.PARAMETER


# ---------------------------------------------------------------------------
# ASTRoot Tests
# ---------------------------------------------------------------------------

def test_ast_root_metrics_recalculation():
    root_node = make_node(NodeType.MODULE, "app")
    c1 = make_node(NodeType.CLASS, "Service")
    m1 = make_node(NodeType.METHOD, "run")

    root_node.add_child(c1)
    c1.add_child(m1)

    ast_root = ASTRoot(
        file_path="src/app.py",
        language="python",
        root_node=root_node,
    )

    assert ast_root.root_id.startswith("tree-")
    ast_root.recalculate_metrics()

    assert ast_root.total_nodes == 3
    assert ast_root.max_depth == 3


def test_ast_root_lookup():
    root_node = make_node(NodeType.MODULE, "module")
    child = make_node(NodeType.FUNCTION, "target_fn")
    root_node.add_child(child)

    ast_root = ASTRoot(
        file_path="src/module.py",
        language="python",
        root_node=root_node,
    )

    found = ast_root.get_node_by_id(child.node_id)
    assert found is not None
    assert found.name == "target_fn"

    nodes = ast_root.find_nodes(lambda n: n.type == NodeType.FUNCTION)
    assert len(nodes) == 1
    assert nodes[0].name == "target_fn"


def test_ast_root_serialization_round_trip():
    root_node = make_node(NodeType.MODULE, "main")
    fn = make_node(NodeType.FUNCTION, "calculate")
    root_node.add_child(fn)

    ast_root = ASTRoot(
        file_path="src/main.py",
        language="python",
        root_node=root_node,
    )

    json_str = ast_root.model_dump_json()
    data = json.loads(json_str)

    assert data["file_path"] == "src/main.py"
    assert data["language"] == "python"
    assert data["root_node"]["name"] == "main"
    assert data["root_node"]["children"][0]["name"] == "calculate"

    # Deserialization
    restored = ASTRoot.model_validate(data)
    assert restored.root_id == ast_root.root_id
    assert restored.root_node.children[0].name == "calculate"
