# Planner Lifecycle & State Transitions

## Purpose
`PlannerState` and `PlannerLifecycle` manage the deterministic state transitions of a planning request session.

---

## State Transition Diagram

```
[CREATED] ---> [INITIALIZED] ---> [VALIDATING] ---> [PLANNING] ---> [OPTIMIZING] ---> [BUILDING_PLAN] ---> [COMPLETED]
    |               |                 |                 |                |                  |
    v               v                 v                 v                v                  v
 [FAILED]        [FAILED]          [FAILED]          [FAILED]         [FAILED]           [FAILED]
 [CANCELLED]     [CANCELLED]       [CANCELLED]       [CANCELLED]      [CANCELLED]        [CANCELLED]
                                                     [TIMEOUT]        [TIMEOUT]          [TIMEOUT]
```

---

## Terminal States
- **`COMPLETED`**: Planning pipeline finished successfully.
- **`FAILED`**: An unhandled exception or error occurred during planning.
- **`CANCELLED`**: Planning request was cancelled by user/client.
- **`TIMEOUT`**: Planning request exceeded `PlanningBudget.timeout_seconds`.
