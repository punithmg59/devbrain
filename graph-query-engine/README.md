# DevBrain Graph Query Engine

High-performance graph query execution, reasoning, and dependency analysis engine for DevBrain.

## Subsystem Architecture Overview

The `graph-query-engine` package forms the query execution and intelligence layer of DevBrain. It provides high-performance graph traversal, pattern matching, dependency reasoning, and static graph view evaluation.

## Key Package Foundations (Step 1)

- **Configuration Management**: Strongly typed configuration loader, defaults, and environment overrides (`src/config/`).
- **Error Framework**: Hierarchical error system supporting error codes, causes, and metadata (`src/error/`).
- **Shared Types & Nominal IDs**: Compile-time branded types (`NodeId`, `EdgeId`, `SymbolId`, etc.) and system enums (`src/types/`).
- **Engine Lifecycle & DI Contracts**: Service registry, lifecycle components, and disposable resource abstractions (`src/shared/`).
- **Logging & Diagnostics**: Structured logging and logger factory interfaces (`src/diagnostics/`).
- **Utilities**: Functional `Result`, `Option`, assertions, UUID generators, and deep immutability helpers (`src/utils/`).

## Documentation

Detailed architecture documentation is located in the `docs/` directory:
- [Architecture.md](./docs/Architecture.md)
- [FolderStructure.md](./docs/FolderStructure.md)
- [CodingStandards.md](./docs/CodingStandards.md)

## Development

```bash
# Typecheck TypeScript sources
npm run typecheck

# Build JavaScript and declaration files
npm run build
```
