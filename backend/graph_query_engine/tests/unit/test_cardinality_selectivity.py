"""
Unit test suite for CardinalityEstimator and SelectivityEstimator.
"""

from graph_query_engine.cost import CardinalityEstimator, GraphStatisticsMetadata, SelectivityEstimator
from graph_query_engine.logical import LogicalOperatorBuilder
from graph_query_engine.query import PredicateBuilder


def test_selectivity_estimator():
    eq_id = PredicateBuilder.eq("id", "sym_123")
    sel_id = SelectivityEstimator.estimate_predicate_selectivity(eq_id)
    assert sel_id == 0.001

    eq_gen = PredicateBuilder.eq("kind", "FUNCTION")
    sel_gen = SelectivityEstimator.estimate_predicate_selectivity(eq_gen)
    assert sel_gen == 0.05

    and_pred = PredicateBuilder.and_combine(eq_id, eq_gen)
    sel_and = SelectivityEstimator.estimate_predicate_selectivity(and_pred)
    assert sel_and < sel_gen


def test_cardinality_estimator():
    stats = GraphStatisticsMetadata()

    lookup_op = LogicalOperatorBuilder.lookup("sym_1")
    c_lookup = CardinalityEstimator.estimate_operator_cardinality(lookup_op, ())
    assert c_lookup == 1.0

    expand_op = LogicalOperatorBuilder.expand()
    c_expand = CardinalityEstimator.estimate_operator_cardinality(expand_op, (10.0,), stats)
    assert c_expand == 50.0  # 10 * 5.0
