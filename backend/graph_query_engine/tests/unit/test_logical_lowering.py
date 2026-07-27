"""
Unit test suite for AST lowering rules and unknown node handling.
"""

import pytest

from graph_query_engine.logical import (
    ASTLoweringPipeline,
    UnknownOperatorError,
)
from graph_query_engine.query import ASTBuilder, EngineeringQuery, QueryBuilder, SymbolReference


def test_ast_lowering_unknown_operator_raises_error():
    class DummyUnknownASTContent:
        pass

    dummy_node = ASTBuilder.create_node(content=DummyUnknownASTContent(), node_id="dummy_1")
    dummy_ast = ASTBuilder.create_ast(dummy_node)

    query = QueryBuilder(name="DummyQuery").build()
    invalid_query = EngineeringQuery.model_construct(
        query_id=query.query_id,
        version=query.version,
        metadata=query.metadata,
        options=query.options,
        planner_options=query.planner_options,
        source_info=query.source_info,
        diagnostics=query.diagnostics,
        constraints=query.constraints,
        result_spec=query.result_spec,
        ast=dummy_ast,
    )

    pipeline = ASTLoweringPipeline()
    with pytest.raises(UnknownOperatorError) as exc_info:
        pipeline.lower_query(invalid_query)

    assert exc_info.value.stage == "ASTLowering"
    assert "DummyUnknownASTContent" in str(exc_info.value)
