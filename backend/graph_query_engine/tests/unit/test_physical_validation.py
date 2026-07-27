"""
Unit test suite for PhysicalPlanValidator rules.
"""

from graph_query_engine.physical import PhysicalPlanBuilder, PhysicalPlanValidator


def test_physical_plan_validator_clean():
    plan = PhysicalPlanBuilder().with_index_lookup("sym_val_1").build()
    report = PhysicalPlanValidator.validate(plan)

    assert report.is_valid is True
    assert len(report.violations) == 0
