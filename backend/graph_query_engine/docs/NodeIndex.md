# NodeIndex Documentation

## Purpose
`NodeIndex` provides deterministic O(1) lookups over graph nodes by `NodeId`.

---

## API Surface
- `contains(node_id: NodeId | str) -> bool`
- `get(node_id: NodeId | str) -> ImmutableNodeView` (raises `IndexLookupError` if missing)
- `try_get(node_id: NodeId | str) -> Optional[ImmutableNodeView]`
- `exists(node_id: NodeId | str) -> bool`
- `size() -> int`
- `keys() -> tuple[NodeId, ...]`
- `values() -> tuple[ImmutableNodeView, ...]`
- `items() -> tuple[tuple[NodeId, ImmutableNodeView], ...]`

---

## Invariants
- Zero graph traversal algorithms.
- Read-only and thread-safe.
