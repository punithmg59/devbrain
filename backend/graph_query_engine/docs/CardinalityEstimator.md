# Cardinality Estimator Specification

## Overview
`CardinalityEstimator` computes expected output row/entity counts, branching factors, and fan-out degrees for logical operators.

---

## Calculations
- `LogicalLookupOperator`: Cardinality = 1.0.
- `LogicalExpandOperator`: Cardinality = Input * (average_degree ^ depth).
- `LogicalFilterOperator`: Cardinality = Input * predicate_selectivity.
- `LogicalLimitOperator`: Cardinality = min(Input, limit).
- `LogicalJoinOperator`: Cardinality = Left_card * Right_card * join_selectivity.
