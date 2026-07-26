# Graph Query Engine (`graph_query_engine`)

The **Graph Query Engine** is the deterministic graph access layer for DevBrain's AI Change Intelligence Platform.

## Purpose

The Graph Query Engine provides read-only, high-performance, deterministic access to immutable graph snapshots produced by DevBrain's repository analyzers and graph storage modules.

### Responsibilities
- Read immutable graph snapshots
- Execute deterministic graph queries
- Perform graph traversals (BFS, DFS, Shortest Path, Reachability)
- Query secondary indexes
- Return typed, deterministic query result sets

### Explicit Out-of-Scope (DO NOT DO)
- Repository parsing / AST analysis
- Graph persistence or segment storage
- In-place graph modification or mutation
- AI reasoning / LLM generation
- Blast radius calculation (handled by upstream engine)
- Graph diffing / version comparison

---

## Package Architecture & Principles

- **Clean Architecture & SOLID Principles**: Clear separation between api, model, config, errors, lifecycle, logging, and traversal.
- **Strong Typing**: Extensive use of `typing.NewType`, Pydantic v2 immutable models, and strict type hints.
- **Zero Business Logic in Step 1**: Step 1 creates only the enterprise foundation, contracts (`typing.Protocol`), primitive domain types, error handling hierarchy, and configuration loaders.
- **No Global Mutable State / Singletons**: All components are disposable, testable, and dependency-injected.

---

## Future Evolution Roadmap

1. **Step 1**: Foundation & Infrastructure (Completed)
2. **Step 2**: GraphView & Storage Read Adapter Integration
3. **Step 3**: Deterministic Query Planner & AST
4. **Step 4**: Traversal Engine (BFS, DFS, SCC, Shortest Path)
5. **Step 5**: Secondary Indexes & Query Cache
6. **Step 6**: Execution Pipeline & Resource Budget Enforcement
