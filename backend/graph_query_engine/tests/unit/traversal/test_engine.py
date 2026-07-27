# backend/graph_query_engine/tests/unit/traversal/test_engine.py
"""End-to-end unit tests for TraversalEngine facade."""

from graph_query_engine.traversal import (
    TraversalEngine,
    TraversalResult,
    TraversalPipeline,
    NeighborExpandOperator,
)


def get_graph():
    return {
        "modA": [("modB", {})],
        "modB": [("modC", {})],
        "modC": [],
    }


def test_traversal_engine_execute_algorithm():
    engine = TraversalEngine()
    result = engine.execute_algorithm(
        algorithm="bfs",
        graph_view=get_graph(),
        start_nodes=["modA"],
    )

    assert isinstance(result, TraversalResult)
    assert "modA" in result.visited_nodes
    assert "modB" in result.visited_nodes
    assert "modC" in result.visited_nodes


def test_traversal_engine_execute_pipeline():
    engine = TraversalEngine()
    pipeline = TraversalPipeline(operators=[
        NeighborExpandOperator(direction="OUTGOING")
    ])

    result = engine.execute_pipeline(
        pipeline=pipeline,
        graph_view=get_graph(),
        start_nodes=["modA"],
    )

    assert result.visited_nodes == ["modB"]


def test_traversal_engine_execute_plan():
    engine = TraversalEngine()

    class MockStage:
        def __init__(self):
            self.operators = [type("MockOp", (), {"params": {"start_nodes": ["modA"]}})()]

    class MockExecutionPlan:
        def __init__(self):
            self.stages = [MockStage()]

    plan = MockExecutionPlan()
    result = engine.execute_plan(plan, graph_view=get_graph())

    assert "modA" in result.visited_nodes
