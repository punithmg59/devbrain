"""
Unit test suite for fluent QueryBuilder immutability and query construction.
"""

from graph_query_engine.query import PredicateBuilder, QueryBuilder


def test_query_builder_immutability():
    b1 = QueryBuilder(name="InitialQuery").with_lookup("sym_100")
    b2 = b1.with_name("UpdatedQuery")
    b3 = b2.with_time_budget(60.0)

    assert b1._name == "InitialQuery"
    assert b2._name == "UpdatedQuery"
    assert b3._time_budget_sec == 60.0

    q1 = b1.build()
    q2 = b2.build()
    q3 = b3.build()

    assert q1.metadata.name == "InitialQuery"
    assert q2.metadata.name == "UpdatedQuery"
    assert q3.constraints.time_budget.max_seconds == 60.0


def test_query_builder_fluent_filter_and_projection():
    pred = PredicateBuilder.eq("language", "python")
    query = (
        QueryBuilder(name="FilterQuery")
        .with_lookup("sym_proc", name="process_job")
        .with_filter(pred)
        .with_projection("id", "name", "file")
        .build()
    )

    assert query.metadata.name == "FilterQuery"
    assert query.result_spec.projection.projected_fields == ("id", "name", "file")
    assert query.ast.root_node.content.operator_type == "FILTER"
