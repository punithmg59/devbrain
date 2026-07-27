"""
Unit test suite for ExecutionPlanValidator rules and DAG cycle detection.
"""

from graph_query_engine.execution import (
    ExecutionPlan,
    ExecutionPlanBuilder,
    ExecutionPlanValidator,
    ExecutionStageBuilder,
    StageDependencyGraph,
)


def test_execution_plan_validator_clean():
    stage1 = ExecutionStageBuilder.lookup_stage("sym_1", stage_id="s1")
    stage2 = ExecutionStageBuilder.filter_stage(stage_id="s2", dependencies=("s1",))

    plan = ExecutionPlanBuilder().with_stage(stage1).with_stage(stage2).build()
    report = ExecutionPlanValidator.validate(plan)

    assert report.is_valid is True
    assert len(report.violations) == 0


def test_execution_plan_validator_cyclic_dag():
    # Construct cyclic dependency graph (s1 depends on s2, s2 depends on s1)
    dag_cyclic = StageDependencyGraph(
        stage_ids=("s1", "s2"),
        dependency_edges={"s1": ("s2",), "s2": ("s1",)},
        topological_order=("s1", "s2"),
    )
    assert dag_cyclic.is_acyclic() is False
