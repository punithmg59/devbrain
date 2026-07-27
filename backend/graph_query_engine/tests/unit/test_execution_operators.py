"""
Unit test suite for Execution Operators immutability and attributes.
"""

import pytest
from pydantic import ValidationError

from graph_query_engine.execution import IndexLookupExecutionOperator


def test_execution_operator_immutability():
    eop = IndexLookupExecutionOperator(
        execution_operator_id="eop_123",
        index_name="PRIMARY_INDEX",
    )
    assert eop.operator_name == "INDEX_LOOKUP_EXEC"

    with pytest.raises((ValidationError, TypeError)):
        eop.index_name = "MUTATED_INDEX"
