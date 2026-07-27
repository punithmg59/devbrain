# Query Structural Validation Specification

## Overview
`QueryValidator` validates the structural integrity, type bounds, required fields, and operator consistency of `EngineeringQuery` instances.

---

## Validation Scope
- Verify presence and formatting of `query_id`.
- Validate AST node structure using `ValidationVisitor`.
- Validate resource constraints (positive budget limits for time, memory, node counts).
- **Does NOT** perform graph lookups, plan generation, or query execution.

---

## Output
Returns `ValidationReport`:
- `is_valid`: Boolean flag indicating if query is structurally sound.
- `violations`: List of `ValidationViolation` records.
