# Logical Validation Specification

## Overview
`LogicalPlanValidator` enforces structural integrity invariants on generated `LogicalPlan` trees.

---

## Checked Invariants
- Verify non-empty `plan_id` and `query_id`.
- Validate required fields across all logical operator models.
- Verify binary operator child counts (e.g. `LogicalJoinOperator` must have exactly 2 child inputs).
- **Does NOT** perform cost model validation or physical index availability checks.
