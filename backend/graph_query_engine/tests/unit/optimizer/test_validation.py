# backend/graph_query_engine/tests/unit/optimizer/test_validation.py
"""Unit tests for OptimizerValidator invariant checking."""

import pytest
from graph_query_engine.optimizer import (
    PhysicalPlan,
    OptimizedPhysicalPlan,
    OptimizerValidator,
)


def test_validator_clean_pass():
    before = PhysicalPlan(operators=[{"type": "scan", "params": {}}])
    after = OptimizedPhysicalPlan(operators=[{"type": "index_scan", "params": {}}])
    OptimizerValidator.validate(before, after)


def test_validator_rejects_empty_to_nonempty():
    before = PhysicalPlan(operators=[])
    after = OptimizedPhysicalPlan(operators=[{"type": "scan", "params": {}}])
    with pytest.raises(ValueError, match="Optimized plan has operators while original plan was empty"):
        OptimizerValidator.validate(before, after)


def test_validator_rejects_missing_type():
    before = PhysicalPlan(operators=[{"type": "scan", "params": {}}])
    after = OptimizedPhysicalPlan(operators=[{"params": {}}])  # Missing 'type'
    with pytest.raises(KeyError, match="missing required 'type' field"):
        OptimizerValidator.validate(before, after)
