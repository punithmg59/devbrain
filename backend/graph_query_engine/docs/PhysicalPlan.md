# PhysicalPlan Specification

## Overview
`PhysicalPlan` is the canonical output model of Step 4.5.

---

## Model Fields
- `plan_id`: Unique `pplan_*` identifier string.
- `logical_plan_id`: Associated source `LogicalPlan` plan_id.
- `query_id`: Source `QueryId`.
- `version`: `PhysicalPlanVersion` instance.
- `metadata`: `PhysicalPlanMetadata` (node_count, depth, strategy_name, rationales).
- `total_cost_estimate`: Estimated cost from `CostReport`.
- `root_node`: `PhysicalPlanNode` tree root.
- `diagnostics`: Physical planner diagnostic items tuple.
