# Query Model Specification

## Overview
`EngineeringQuery` is the canonical root representation model for all engineering queries in DevBrain.

---

## Model Components

### 1. `EngineeringQuery` (Root Model)
- `query_id`: Unique `QueryId` string.
- `version`: Associated `QueryVersion` model.
- `metadata`: `QueryMetadata` annotations.
- `options`: `QueryOptions` execution behavior flags.
- `planner_options`: `PlannerQueryOptions` optimization hints.
- `source_info`: `SourceInfo` tracing and origin system context.
- `diagnostics`: `QueryDiagnosticsMetadata` location & warning payload.
- `constraints`: `QueryConstraints` resource limits container.
- `result_spec`: `ResultSpecification` output shaping spec.
- `ast`: `QueryAST` tree root node.

### 2. Immutability Contract
All fields are frozen on instantiation. Modifications are performed exclusively via `QueryBuilder` or model copy methods producing new instances.
