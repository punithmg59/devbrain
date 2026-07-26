# Architecture Specification: Graph Query Engine

## System Overview

The **Graph Query Engine** is a core component of Phase 2 (Graph Intelligence Platform) in DevBrain. It operates directly above **Graph Storage** to execute pattern-based queries, graph traversals, and static graph view projections.

```
┌─────────────────────────────────────────────────────────────┐
│               Future Reasoning Subsystems                  │
│ (Blast Radius Engine, Graph Diff Engine, Overlay Engine)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 DevBrain Graph Query Engine                 │
│ ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────────┐ │
│ │    API    │  │ Planner   │  │ Traversal │  │ GraphView  │ │
│ └───────────┘  └───────────┘  └───────────┘  └────────────┘ │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Graph Storage                          │
└─────────────────────────────────────────────────────────────┘
```

## Core Architectural Layers

1. **API Layer (`src/api/`)**: Public request/response contracts for query invocation.
2. **Planner Layer (`src/planner/`)**: Query optimization, plan generation, and execution cost estimation.
3. **Pipeline Layer (`src/pipeline/`)**: Stage-based query execution pipeline orchestrator.
4. **Traversal Layer (`src/traversal/`)**: Core graph search abstractions (BFS, DFS, shortest path).
5. **View Layer (`src/view/`)**: Immutable snapshot graph projections (`GraphView`).
6. **Index Layer (`src/index/`)**: Fast node/symbol/relationship lookup structures.
7. **Infrastructure Foundation (`src/config/`, `src/error/`, `src/shared/`, `src/utils/`)**: Universal cross-cutting utilities, logging, errors, configuration, and dependency contracts.

## Architectural Principles

- **Clean Architecture & Layer Separation**: Inner layers know nothing about outer layers.
- **Dependency Inversion**: High-level components depend on abstract interfaces (`ServiceRegistry`, `Logger`, `UuidGenerator`).
- **Immutable Data Boundaries**: All configuration, error metadata, and domain descriptors use immutable data structures (`Readonly<T>`, `freezeDeep`).
- **Nominal Identifier Safety**: Branded primitives (`NodeId`, `QueryId`) prevent ID swapping bugs at compile time.
