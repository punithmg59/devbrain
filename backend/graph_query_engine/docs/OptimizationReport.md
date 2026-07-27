# Optimization Report & Metrics

## Overview

The `OptimizationReport` is an immutable summary produced by `PlannerOptimizer.optimize_with_report()`.

It aggregates:
- Original input plan (`before_plan`)
- Transformed output plan (`after_plan`)
- List of applied rules (`applied_rules`)
- List of skipped rules (`skipped_rules`)
- List of rejected rules (`rejected_rules`)
- Quantitative structural metrics (`metrics`)

---

## Metrics Breakdown

`OptimizationMetrics` tracks structural counters:

- `operators_removed`: Count of eliminated operators.
- `operators_merged`: Count of fused operator pairs.
- `depth_reduction`: Reduction in physical operator tree depth.
- `pipeline_reduction`: Reduction in pipeline execution steps.
- `join_improvements`: Reordered or simplified join operations.
- `projection_reductions`: Eliminated or pushed-down projections.
- `filter_reductions`: Eliminated or pushed-down filters.
- `estimated_complexity_reduction`: Quantitative heuristic score of transformation benefit.
