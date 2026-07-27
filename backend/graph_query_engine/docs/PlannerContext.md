# PlannerContext Documentation

## Purpose
`PlannerContext` is an immutable state container passed through every stage of the planning pipeline.

---

## Architectural Rules
1. **Strict Immutability**: `PlannerContext` is a frozen model (`ConfigDict(frozen=True)`).
2. **NO Graph Data**: Must **NOT** contain `GraphView`, node views, edge views, or raw graph payload data.
3. **Metadata & References Only**: Contains `session_id`, `correlation_id`, `query_metadata`, `configuration`, `budget`, `diagnostics`, `snapshot_metadata_ref`, `index_metadata_ref`, `planning_options`, and `planner_state`.
