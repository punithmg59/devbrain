# ExecutionPlan Specification

## Overview
`ExecutionPlan` is the canonical output model of Step 4.6.

---

## Model Fields
- `execution_plan_id`: Unique `eplan_*` identifier string.
- `physical_plan_id`: Associated input `PhysicalPlan` plan_id.
- `query_id`: Source `QueryId`.
- `version`: `ExecutionPlanVersion` instance.
- `metadata`: `ExecutionMetadata` (timeout_ms, max_memory_bytes, checkpoint_enabled, cancellation_token_id, progress_tracking_id).
- `stages`: Tuple of `ExecutionStage` objects.
- `dependency_graph`: `StageDependencyGraph` DAG mapping dependencies and topological execution order.
- `pipeline`: `ExecutionPipeline` ordered container.
- `estimated_runtime_ms`: Estimated total runtime in milliseconds.
- `diagnostics`: Execution planner diagnostic items tuple.
