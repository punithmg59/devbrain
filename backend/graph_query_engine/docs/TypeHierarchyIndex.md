# TypeHierarchyIndex Documentation

## Purpose
`TypeHierarchyIndex` provides O(1) lookups for OOP type inheritance graphs, mapping classes to base parent types, derived child types, and overrides.

---

## API Surface
- `base_classes(node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]`
- `derived_classes(node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]`
- `parents(node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]`
- `children(node_id: NodeId | str) -> tuple[ImmutableNodeView, ...]`
