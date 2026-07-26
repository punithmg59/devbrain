# Folder Structure & Responsibility Mapping

| Folder | Single Responsibility |
| :--- | :--- |
| `src/api/` | Public query engine request, response, and payload contracts. |
| `src/model/` | Domain graph reference models, query AST nodes, and data structures. |
| `src/pipeline/` | Multi-stage query execution pipeline contracts and orchestrators. |
| `src/planner/` | Query plan representation, cost estimation, and plan optimization. |
| `src/traversal/` | Graph traversal abstractions, options, and search specifications. |
| `src/index/` | Secondary indexing interfaces for symbols, files, and node lookup. |
| `src/view/` | Immutable static graph view projections (`GraphView`). |
| `src/validation/` | Query validation, syntax checking, and static constraint evaluation. |
| `src/diagnostics/` | Logging abstractions (`Logger`, `LoggerFactory`), telemetry, and diagnostic traces. |
| `src/config/` | Engine configuration models, default options, validation, and env loaders. |
| `src/budget/` | Traversal step, node limit, and execution time budget tracking contracts. |
| `src/capabilities/` | Capability matrix and feature availability checking. |
| `src/extension/` | Extension plugin interfaces and custom operator hooks. |
| `src/error/` | Base `GraphQueryError` hierarchy (`ConfigurationError`, `ValidationError`, etc.). |
| `src/shared/` | Centralized constants, lifecycle contracts (`EngineState`), and DI interfaces (`ServiceRegistry`). |
| `src/utils/` | Shared utilities (`Assertions`, `Result<T,E>`, `Option<T>`, `UuidGenerator`, `freezeDeep`). |
| `src/types/` | Branded nominal identifier types (`NodeId`, `QueryId`) and domain enums. |
| `test/unit/` | Fast unit test suites for individual components. |
| `test/integration/` | End-to-end integration tests between subsystems. |
| `test/benchmark/` | Performance profiling and latency benchmark suites. |
| `test/property/` | Property-based tests verifying invariant correctness. |
| `test/stress/` | High-load concurrency and memory stress tests. |
| `docs/` | System architecture, folder specs, coding standards, and developer guides. |
