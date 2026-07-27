# Optimizer Validation

## Overview

The `OptimizerValidator` provides lightweight structural and semantic validation for physical plans before and after optimization.

---

## Invariant Assertions

1. **Model Integrity**: Input must be a valid `PhysicalPlan`, output must be a valid `OptimizedPhysicalPlan`.
2. **Operator Schema**: Every operator must be a dictionary containing a string `type` key.
3. **Empty Plan Protection**: An optimized plan cannot introduce operators if the original plan was empty.
4. **Semantic Preservation**: Verifies operator types compatibility.
