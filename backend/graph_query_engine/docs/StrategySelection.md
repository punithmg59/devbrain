# Strategy Selection Specification

## Overview
Strategy selectors choose physical algorithms driven by operator requirements and `CostReport` metrics.

---

## Strategy Selection Rules
1. **Lookup Strategy**: Selects `IndexLookupPhysicalOperator` when primary/symbol index references exist; falls back to `SequentialLookupPhysicalOperator`.
2. **Expand Strategy**: Selects `BreadthExpandPhysicalOperator` for shallow depths ($\le 3$), and `DepthExpandPhysicalOperator` for deep path traversals ($> 3$).
3. **Join Strategy**: Selects `NestedLoopJoinPhysicalOperator` for low cardinality ($< 20$), and `HashJoinPhysicalOperator` for larger input streams.
4. **Pushdown Strategy**: Generates `FilterPushdownPhysicalOperator` and `ProjectionPushdownPhysicalOperator` to reduce intermediate tuple widths.
