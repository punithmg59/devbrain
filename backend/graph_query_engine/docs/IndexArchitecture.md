# Index Infrastructure Architecture Documentation

## Purpose
The Index Infrastructure package (`graph_query_engine.index`) establishes the foundational architecture for all secondary graph indexes in DevBrain.

Indexes enable O(1) symbol lookups, file paths, namespace resolution, type hierarchies, and edge traversals for query execution.

---

## Architectural Principles
1. **Immutability**: All indexes inherit from `BaseIndex` and are constructed as frozen, read-only data structures.
2. **Contract Isolation**: All index abstractions are defined as Python `Protocol` interfaces in `graph_query_engine.contracts.index`.
3. **Stateless Transformation**: Index construction is performed via `IndexBuilder` and `IndexFactory` from immutable `GraphView` snapshots.
4. **Thread Safety**: Read-only mappings and thread-safe registries (`IndexRegistry`) ensure safe parallel query execution across threads.

---

## Component Layers
- **`BaseIndex`**: Root parent model for all future concrete indexes (`SymbolIndex`, `FileIndex`, `CSRIndex`, etc.).
- **`IndexDescriptor`**: Immutable metadata definition specifying index capabilities, semver bounds, and dependencies.
- **`IndexMetadata`**: Provenance tracking completed build timing, source graph version, and checksum placeholders.
- **`IndexStatistics`**: RAM footprint estimates, node/edge counts, and lookup statistics placeholders.
