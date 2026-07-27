# Query Planner Core Infrastructure Architecture

## Overview
The Planner Core Infrastructure (`graph_query_engine.planner`) provides the foundational state containers, configuration models, lifecycle managers, diagnostics collectors, capabilities registries, metrics, and extension protocols for the Query Planner.

---

## Component Layering

```
                     IPlannerContext / IPlannerSession (Contracts)
                                       |
                                PlannerContext
                               /       |      \
                              /        |       \
             PlannerConfiguration  PlannerBudget  PlannerDiagnostics
```

---

## Key Infrastructure Components
1. **`PlannerVersion`**: Semver representation (`major.minor.patch-genX`).
2. **`PlannerState`**: Enum tracking lifecycle states (`CREATED`, `INITIALIZED`, `VALIDATING`, `PLANNING`, `OPTIMIZING`, `BUILDING_PLAN`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMEOUT`).
3. **`PlannerLifecycle`**: Thread-safe lifecycle manager for state transitions.
4. **`PlanningBudget`**: Immutable budget configuration (timeout, max stages, max iterations, memory limits, operator limits).
5. **`PlannerConfiguration`**: Immutable planner configuration flags (optimization, diagnostics, cost estimation, validation, debug/strict flags).
6. **`PlannerCapabilities`**: Capability registry advertising supported features (`LOGICAL_PLANNING`, `COST_ESTIMATION`, `OPTIMIZATION`, etc.).
7. **`PlannerDiagnostics` & `DiagnosticEvent`**: Thread-safe event collector for diagnostic items, timings, warnings, and trace logs.
8. **`PlannerMetrics` & `MetricsCollector`**: Aggregates operational metrics for telemetry reporting.
9. **`PlannerContext`**: Immutable stage context container passed through every planner stage. **Contains NO `GraphView` or graph data**.
10. **`PlannerSession`**: Request session manager tracking session ID, correlation, version, and lifecycle.
11. **`PlannerValidation`**: Infrastructure validator for context, config, budget, and state transitions.
12. **`PlannerRegistry`**: Thread-safe extension registry for future optimizers, physical planners, validators, and diagnostic listeners.
