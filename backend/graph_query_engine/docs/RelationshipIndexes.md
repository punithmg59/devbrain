# Relationship Indexes Architectural Documentation

## Purpose
The Relationship Index Layer (`CSRAdjacencyIndex`, `ReverseCSRAdjacencyIndex`, `RelationshipIndex`, `OutgoingRelationshipIndex`, `IncomingRelationshipIndex`, `NodeRelationshipIndex`, `RelationshipTypeIndex`, `SelfLoopIndex`) provides fast, read-only adjacency structures over `GraphView` snapshots.

---

## Architectural Role
The Relationship Index Layer serves as the storage engine data access layer for future traversal engines, query planners, and graph analytics engines.

It performs **zero graph traversals**, **zero recursion**, and **zero graph algorithms**.

---

## Complexity & Memory Model

| Index | Primary Lookup Key | Output Structure | Access Time | Space Complexity |
|---|---|---|---|---|
| `CSRAdjacencyIndex` | `NodeId` | `tuple[NodeId, ...]` (targets) | O(1) slice | O(V + E) |
| `ReverseCSRAdjacencyIndex` | `NodeId` | `tuple[NodeId, ...]` (sources) | O(1) slice | O(V + E) |
| `RelationshipIndex` | `EdgeId` | `ImmutableEdgeView` | O(1) | O(E) |
| `OutgoingRelationshipIndex` | `NodeId` | `tuple[ImmutableEdgeView, ...]` | O(1) | O(E) |
| `IncomingRelationshipIndex` | `NodeId` | `tuple[ImmutableEdgeView, ...]` | O(1) | O(E) |
| `NodeRelationshipIndex` | `NodeId` | `tuple[ImmutableEdgeView, ...]` | O(1) | O(E) |
| `RelationshipTypeIndex` | `RelationshipType` | `tuple[ImmutableEdgeView, ...]` | O(1) | O(E) |
| `SelfLoopIndex` | `NodeId` | `tuple[ImmutableEdgeView, ...]` | O(1) | O(SelfLoops) |

---

## Thread Safety & Immutability
- Built once during index construction via `IndexBuilder`.
- All offset arrays (`tuple[int, ...]`) and node mappings are completely frozen.
- Zero locks required during parallel read operations.
