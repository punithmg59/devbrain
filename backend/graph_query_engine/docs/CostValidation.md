# Cost Validation Specification

## Overview
`CostValidator` verifies structural and mathematical invariants of `CostEstimate` and `CostReport` objects.

---

## Checked Invariants
- CPU cost, Memory cost, and Traversal cost must be $\ge 0.0$.
- Confidence scores must be within $[0.0, 1.0]$.
- Non-empty report and plan IDs.
- Valid per-operator breakdown items.
