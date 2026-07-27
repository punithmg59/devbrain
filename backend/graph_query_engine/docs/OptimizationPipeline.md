# Optimization Pipeline & Scheduler

## Overview

The `OptimizationPipeline` and `OptimizationScheduler` form the execution engine of the `PlannerOptimizer`.

The pipeline executes optimization phases in topological dependency order. Within each phase, rules are evaluated according to their priority.

The scheduler wraps the pipeline in a fixed-point iteration loop, continuing passes until no rules produce changes or `max_iterations` (default 10) is reached.

---

## Phase Execution Sequence

```mermaid
graph LR
    P1["1. Scan Phase"] --> P2["2. Expression Phase"]
    P2 --> P3["3. Filter Phase"]
    P3 --> P4["4. Projection Phase"]
    P4 --> P5["5. Fusion Phase"]
    P5 --> P6["6. Graph Phase"]
    P6 --> P7["7. Cleanup Phase"]
```

---

## Convergence Detection

Convergence is achieved when `plan.operators` at iteration `k` is identical to `plan.operators` at iteration `k-1`.

```mermaid
stateDiagram-v2
    [*] --> PassStart
    PassStart --> RunPipeline
    RunPipeline --> CheckChanged
    CheckChanged --> PassStart: Plan Changed (Iteration < Max)
    CheckChanged --> Converged: Plan Unchanged
    CheckChanged --> MaxReached: Iteration == Max
    Converged --> [*]
    MaxReached --> [*]
```
