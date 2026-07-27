"""
Unit test suite for Lookup, Expand, and Join strategy selectors.
"""

from graph_query_engine.logical import (
    LogicalExpandOperator,
    LogicalJoinOperator,
    LogicalLookupOperator,
)
from graph_query_engine.physical import (
    ExpandStrategySelector,
    JoinStrategySelector,
    LookupStrategySelector,
    PhysicalPlannerDiagnostics,
)
from graph_query_engine.query.references import SymbolReference
from graph_query_engine.query.traversal import TraversalConstraint, TraversalRequest
from graph_query_engine.types import SymbolId


def test_lookup_strategy_selection():
    diag = PhysicalPlannerDiagnostics()
    ref = SymbolReference(identifier="sym_123", symbol_id=SymbolId("sym_123"), name="test_sym")
    lookup_op = LogicalLookupOperator(operator_id="op_look_1", target_reference=ref)

    phys_op = LookupStrategySelector.select_strategy(lookup_op, None, diag)
    assert phys_op.operator_name == "INDEX_LOOKUP"


def test_expand_strategy_selection():
    diag = PhysicalPlannerDiagnostics()
    req_deep = TraversalRequest(constraints=TraversalConstraint(max_depth=5))
    expand_op = LogicalExpandOperator(operator_id="op_exp_1", traversal_request=req_deep)

    phys_op = ExpandStrategySelector.select_strategy(expand_op, None, diag)
    assert phys_op.operator_name == "DEPTH_EXPAND"
