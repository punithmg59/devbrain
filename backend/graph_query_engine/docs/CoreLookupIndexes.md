# Core Lookup Indexes Architectural Documentation

## Purpose
The Core Lookup Indexes layer (`NodeIndex`, `EdgeIndex`, `SymbolIndex`, `FileIndex`, `PackageIndex`, `NamespaceIndex`, `QualifiedNameIndex`) provides deterministic O(1) dictionary-backed lookups over immutable `GraphView` snapshots.

---

## Complexity & Memory Model

| Index | Primary Key | Value Structure | Time Complexity | Memory Allocation |
|---|---|---|---|---|
| `NodeIndex` | `NodeId` | `ImmutableNodeView` | O(1) | O(V) |
| `EdgeIndex` | `EdgeId` | `ImmutableEdgeView` | O(1) | O(E) |
| `SymbolIndex` | `SymbolId` | `ImmutableNodeView` | O(1) | O(S) |
| `FileIndex` | `FileId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `PackageIndex` | `PackageId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `NamespaceIndex` | `NamespaceId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `QualifiedNameIndex` | `str` | `ImmutableNodeView` | O(1) | O(V) |

---

## Thread Safety & Immutability
- Indexes are constructed once during engine initialization or graph snapshot creation via `IndexBuilder`.
- Lookups operate over immutable mappings (`MappingProxyType` or frozen dicts), guaranteeing zero locks during concurrent read operations.
