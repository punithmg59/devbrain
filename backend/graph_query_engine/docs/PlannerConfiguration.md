# PlannerConfiguration & PlanningBudget Documentation

## Purpose
`PlannerConfiguration` and `PlanningBudget` define the behavior, flags, and budget resource limits for planning request execution.

---

## PlanningBudget Parameters
- `timeout_seconds`: Maximum allowed planning duration (seconds).
- `max_planning_stages`: Maximum allowed pipeline stages.
- `max_optimization_iterations`: Maximum optimization rule passes.
- `max_planner_memory_bytes`: Maximum memory footprint for planning (bytes).
- `max_operator_count`: Maximum logical/physical operator count limit.
- `max_estimated_cost`: Maximum allowed estimated cost limit.

---

## PlannerConfiguration Flags
- `optimization_enabled`: Enables/disables optimization rule passes.
- `diagnostics_enabled`: Enables/disables detailed diagnostic event collection.
- `cost_estimation_enabled`: Enables/disables cost model estimation.
- `validation_enabled`: Enables/disables plan validation rules.
- `debug_mode`: Enables trace collection.
- `strict_mode`: Fails immediately on non-critical warnings.
