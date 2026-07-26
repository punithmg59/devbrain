# ReverseCSRAdjacencyIndex Documentation

## Purpose
`ReverseCSRAdjacencyIndex` uses a Reverse Compressed Sparse Row layout to provide O(1) slice lookups for incoming graph neighbors and incoming edge IDs.

---

## Reverse CSR Layout Mechanics
Similar to CSR, but groups edges by target `NodeId` pointing back to source `NodeId`s:
- `node_offsets`: Offset array mapping node index to `source_nodes` slice bounds.
- `source_nodes`: Contiguous array of source `NodeId`s.
- `edge_ids`: Contiguous array of `EdgeId`s corresponding to `source_nodes`.

---

## API Surface
- `incoming_neighbors(node_id: NodeId | str) -> tuple[NodeId, ...]`
- `incoming_edges(node_id: NodeId | str) -> tuple[EdgeId, ...]`
- `in_degree(node_id: NodeId | str) -> int`
- `contains(node_id: NodeId | str) -> bool`
