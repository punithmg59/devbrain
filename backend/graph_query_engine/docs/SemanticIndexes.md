# Semantic Indexes Architectural Documentation

## Purpose
The Semantic Index Layer (`TypeHierarchyIndex`, `InheritanceIndex`, `InterfaceImplementationIndex`, `APIRouteIndex`, `SymbolReferenceIndex`, `ImportIndex`, `ModuleIndex`, `LanguageIndex`, `AnnotationIndex`, `AttributeIndex`) exposes domain-level semantic understandings of repository constructs over `GraphView` snapshots.

---

## Index Class Hierarchy

```
           BaseIndex
           /   |   \
          /    |    \
LookupIndex RelationshipBaseIndex SemanticIndex
    |              |                    |
(NodeIndex,   (CSR, ReverseCSR,    (TypeHierarchy,
 SymbolIndex)  RelTypeIndex)        APIRouteIndex)
```

---

## Complexity & Memory Model

| Index | Primary Key | Output Structure | Complexity | Space |
|---|---|---|---|---|
| `TypeHierarchyIndex` | `NodeId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `InheritanceIndex` | `str` (kind) | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `InterfaceImplementationIndex` | `NodeId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `APIRouteIndex` | `METHOD:PATH` | `APIRouteRecord` | O(1) | O(Routes) |
| `SymbolReferenceIndex` | `NodeId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(E) |
| `ImportIndex` | `FileId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(E) |
| `ModuleIndex` | `str` (module) | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `LanguageIndex` | `LanguageId` | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `AnnotationIndex` | `str` (@ann) | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |
| `AttributeIndex` | `str` (attr) | `tuple[ImmutableNodeView, ...]` | O(1) | O(V) |

---

## Thread Safety & Immutability
- Fully frozen and thread-safe.
- Constructed once via `IndexBuilder`.
- Read-only mappings ensure zero lock contention during parallel query execution.
