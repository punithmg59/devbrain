# Graph Query Engine Public API Contract

This document freezes the public API contract for the **Graph Query Engine** (`graph_query_engine`).

## Public Contracts Surface (`graph_query_engine.contracts`)

The following Python `Protocol` interfaces represent the frozen public contract surface:

| Interface | Module Location | Status |
|---|---|---|
| `IGraphView` | `graph_query_engine.contracts.view` | **STABLE (Frozen)** |
| `IQueryPipeline` | `graph_query_engine.contracts.pipeline` | **STABLE (Frozen)** |
| `IQueryExecutor` | `graph_query_engine.contracts.pipeline` | **STABLE (Frozen)** |
| `IQueryPlanner` | `graph_query_engine.contracts.planner` | **STABLE (Frozen)** |
| `ITraversalStrategy` | `graph_query_engine.contracts.traversal` | **STABLE (Frozen)** |
| `ITraversalRegistry` | `graph_query_engine.contracts.traversal` | **STABLE (Frozen)** |
| `IIndex` | `graph_query_engine.contracts.index` | **STABLE (Frozen)** |
| `IIndexRegistry` | `graph_query_engine.contracts.index` | **STABLE (Frozen)** |
| `IQueryContext` | `graph_query_engine.contracts.model` | **STABLE (Frozen)** |
| `IQueryBudgetManager` | `graph_query_engine.contracts.budget` | **STABLE (Frozen)** |
| `ICapabilityRegistry` | `graph_query_engine.contracts.capabilities` | **STABLE (Frozen)** |
| `ICapabilityValidator` | `graph_query_engine.contracts.capabilities` | **STABLE (Frozen)** |
| `IQueryDiagnostics` | `graph_query_engine.contracts.diagnostics` | **STABLE (Frozen)** |
| `IQueryEngineAPI` | `graph_query_engine.contracts.api` | **STABLE (Frozen)** |
| `IQueryExtension` | `graph_query_engine.contracts.extension` | **STABLE (Frozen)** |
| `IQueryValidator` | `graph_query_engine.contracts.validation` | **STABLE (Frozen)** |

## Core Configuration & Entrypoint Objects

- `GraphQueryEngineConfig` (`graph_query_engine.config`) - Immutable Pydantic v2 configuration.
- `DefaultConfig` (`graph_query_engine.config`) - Canonical default configuration factory.
- `EnvironmentConfiguration` (`graph_query_engine.config`) - Environment variable override loader.
- `GraphQueryError` (`graph_query_engine.errors`) - Base structured exception class.

## Internal Surface (`graph_query_engine.internal.*`)

All sub-packages inside `graph_query_engine.internal` (`planner`, `traversal`, `pipeline`, `cache`, `optimization`, `validation`) are **INTERNAL / PRIVATE**. They carry NO compatibility guarantees and MUST NOT be imported by external components.
