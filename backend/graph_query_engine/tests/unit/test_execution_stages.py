"""
Unit test suite for ExecutionStage immutability, pipeline ordering, and PrintExecutionVisitor.
"""

import pytest
from pydantic import ValidationError

from graph_query_engine.execution import (
    ExecutionPlanBuilder,
    ExecutionStageBuilder,
    PrintExecutionVisitor,
)


def test_execution_stage_immutability():
    stage = ExecutionStageBuilder.lookup_stage("sym_test")
    assert stage.stage_type == "LOOKUP"

    with pytest.raises((ValidationError, TypeError)):
        stage.stage_name = "MUTATED_STAGE"


def test_execution_visitor_print_tree():
    stage1 = ExecutionStageBuilder.lookup_stage("sym_1", stage_id="s1")
    stage2 = ExecutionStageBuilder.filter_stage(stage_id="s2", dependencies=("s1",))

    plan = (
        ExecutionPlanBuilder()
        .with_stage(stage1)
        .with_stage(stage2)
        .build()
    )

    visitor = PrintExecutionVisitor()
    tree_text = visitor.print_plan(plan)

    assert "Stage[s1] -> LOOKUP" in tree_text
    assert "Stage[s2] -> FILTER (depends_on=('s1',))" in tree_text
