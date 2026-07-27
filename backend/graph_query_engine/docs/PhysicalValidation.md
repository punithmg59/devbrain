# Physical Validation Specification

## Overview
`PhysicalPlanValidator` verifies structural and strategy invariants of generated `PhysicalPlan` trees.

---

## Checked Invariants
- Verify non-empty `plan_id` and `logical_plan_id`.
- Validate required configuration fields across physical operator models.
- Verify binary operator input counts (e.g., Physical join operators must have exactly 2 child inputs).
- **Does NOT** perform runtime execution or thread pool validation.
