# Graph Query Engine Architectural Specifications

## Architectural Overview

The Graph Query Engine follows Clean Architecture principles, establishing clear boundaries between configuration, lifecycle management, error handling, domain abstraction, and query execution contracts.

```
       +-------------------------------------------------------+
       |                      api                              |
       +-------------------------------------------------------+
                                  |
                                  v
       +-------------------------------------------------------+
       |             pipeline / planner / traversal             |
       +-------------------------------------------------------+
                 |                    |                    |
                 v                    v                    v
       +-------------------+ +------------------+ +------------+
       |   index / view    | |      budget      | | diagnostics|
       +-------------------+ +------------------+ +------------+
                 |                    |                    |
                 +--------------------+--------------------+
                                      |
                                      v
       +-------------------------------------------------------+
       |  types / constants / errors / config / shared / utils |
       +-------------------------------------------------------+
```

## Layer Descriptions

1. **API Layer (`api/`)**: High-level execution entrypoints exposing standard query interfaces to DevBrain.
2. **Planning & Execution Layer (`planner/`, `pipeline/`)**: Query transformation, logical AST to physical step planning, optimization, and step execution.
3. **Traversal & Algorithms Layer (`traversal/`)**: Core deterministic graph search strategies (BFS, DFS, Shortest Path, SCC).
4. **Index & View Layer (`index/`, `view/`)**: Read-only abstraction layer mapping immutable graph storage snapshots into indexed lookup views (`IGraphView`).
5. **Governance & Resource Layer (`budget/`, `capabilities/`, `diagnostics/`, `validation/`)**: Strict resource timeout/memory budget enforcement, capability validation, and diagnostic profile collection.
6. **Core Infrastructure Layer (`types/`, `constants/`, `errors/`, `config/`, `lifecycle/`, `logging/`, `shared/`, `utils/`)**: Foundation primitives, error handling hierarchy, configuration loader, logging protocols, DI contracts, and monadic utility containers.

---

## Dependency Rules

- High-level packages (`api`, `planner`, `pipeline`, `traversal`) may depend on domain types and contracts (`types`, `model`, `view`, `index`, `shared`, `errors`, `constants`).
- Core infrastructure packages (`types`, `constants`, `errors`, `utils`) MUST NOT depend on higher-level execution packages.
- Zero circular imports permitted.
