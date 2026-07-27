"""
Unit test suite for ResourceEstimator.
"""

from graph_query_engine.cost import ResourceEstimator


def test_resource_estimator_lookup_and_sorting():
    res_lookup = ResourceEstimator.estimate_operator_resources("LOGICAL_LOOKUP", 1.0)
    assert res_lookup.cpu_cycles == 10.0
    assert res_lookup.memory_bytes == 1024.0

    res_sort = ResourceEstimator.estimate_operator_resources("LOGICAL_SORTING", 100.0)
    assert res_sort.cpu_cycles > res_lookup.cpu_cycles
