# Graph Query Engine Dependency & Layering Rules

This document establishes the strict architectural layering rules for the **Graph Query Engine**.

## Architectural Layers (Level Order)

```
Level 110: api
Level 100: core
Level 90:  pipeline
Level 80:  planner
Level 70:  traversal
Level 60:  view, index, budget, capabilities, diagnostics, model, validation
Level 50:  contracts
Level 40:  shared, utils
Level 30:  config, logging, lifecycle
Level 20:  errors
Level 10:  types, constants
```

## Layering Invariants

1. **Downward Imports Only**: High-level layers (e.g. `api`, `core`, `pipeline`) may import lower-level layers (`contracts`, `types`, `errors`, `config`, `utils`).
2. **No Upward Imports**: A lower layer (e.g. `types`, `errors`, `constants`) MUST NEVER import a higher layer (e.g. `api`, `planner`, `pipeline`). Violations will trigger AST lint errors in `scripts/architecture_check.py`.
3. **No Internal Package Leaks**: The package `graph_query_engine.internal.*` is private. It MUST NEVER be imported by any code outside `graph_query_engine.internal`.
4. **No Circular Imports**: Module imports MUST form a Directed Acyclic Graph (DAG). Zero cycles are permitted.
5. **Contract Indirection**: Components must depend on Python Protocols in `graph_query_engine.contracts` rather than concrete implementation classes in `internal/`.
