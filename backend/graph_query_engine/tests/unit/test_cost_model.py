"""
Unit test suite for CostEstimate and CostReport immutability and confidence scores.
"""

import pytest
from pydantic import ValidationError

from graph_query_engine.cost import CostEstimate


def test_cost_estimate_creation_and_bounds():
    est = CostEstimate(cpu_cost=100.0, memory_cost=2048.0, confidence_score=0.9)
    assert est.cpu_cost == 100.0
    assert est.confidence_score == 0.9

    with pytest.raises(ValidationError):
        CostEstimate(confidence_score=1.5)  # Must be <= 1.0

    with pytest.raises(ValidationError):
        CostEstimate(cpu_cost=-10.0)  # Must be >= 0.0


def test_cost_estimate_immutability():
    est = CostEstimate(cpu_cost=50.0)
    with pytest.raises((ValidationError, TypeError)):
        est.cpu_cost = 999.0
