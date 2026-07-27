# LogicalPlan Specification

## Overview
`LogicalPlan` is the canonical output model of Step 4.3.

---

## Model Fields
- `plan_id`: Unique `lplan_*` identifier string.
- `query_id`: Source `QueryId`.
- `version`: `LogicalPlanVersion` instance.
- `metadata`: `LogicalPlanMetadata` (node_count, depth, rules_applied).
- `statistics`: `LogicalPlanStatistics` (cost model placeholder).
- `root_node`: `LogicalPlanNode` tree root.
- `diagnostics`: Diagnostics trace log items tuple.
