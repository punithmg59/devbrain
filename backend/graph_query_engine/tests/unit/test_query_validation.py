"""
Unit test suite for QueryValidator structural validation.
"""

from graph_query_engine.query import (
    EngineeringQuery,
    QueryBuilder,
    QueryConstraints,
    QueryValidator,
    TimeBudgetConstraint,
)


def test_query_validator_valid_query():
    query = QueryBuilder(name="ValidQuery").with_lookup("sym_valid").build()
    report = QueryValidator.validate(query)

    assert report.is_valid is True
    assert len(report.violations) == 0


def test_query_validator_invalid_time_budget():
    query = QueryBuilder(name="BadQuery").with_lookup("sym_1").build()
    bad_constraints = QueryConstraints(
        time_budget=TimeBudgetConstraint.model_construct(max_seconds=-5.0)
    )
    invalid_query = EngineeringQuery.model_construct(
        query_id=query.query_id,
        version=query.version,
        metadata=query.metadata,
        options=query.options,
        planner_options=query.planner_options,
        source_info=query.source_info,
        diagnostics=query.diagnostics,
        constraints=bad_constraints,
        result_spec=query.result_spec,
        ast=query.ast,
    )

    report = QueryValidator.validate(invalid_query)
    assert report.is_valid is False
    assert any(v.rule_id == "RULE_003_TIME_BUDGET" for v in report.violations)
