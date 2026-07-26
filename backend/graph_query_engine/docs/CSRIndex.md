# CSRAdjacencyIndex Documentation

## Purpose
`CSRAdjacencyIndex` uses a Compressed Sparse Row (CSR) array layout to provide cache-friendly O(1) slice access to outgoing graph neighbors and edge IDs.

---

## CSR Layout Mechanics

```
sorted_node_ids: [Node_0, Node_1, Node_2, Node_3]
node_offsets:    [0,      2,      2,      5]

target_nodes:    [Node_1, Node_2, Node_0, Node_1, Node_3]
edge_ids:        [Edge_0, Edge_1, Edge_2, Edge_3, Edge_4]
```

### Slice Lookup Algorithm
For a given `NodeId`:
1. Resolve integer node index `idx` from `node_id_map`.
2. Extract start offset `start = node_offsets[idx]` and end offset `end = node_offsets[idx + 1]`.
3. Return slice `target_nodes[start:end]` or `edge_ids[start:end]`.

---

## API Surface
- `neighbors(node_id: NodeId | str) -> tuple[NodeId, ...]`
- `edge_ids_for(node_id: NodeId | str) -> tuple[EdgeId, ...]`
- `degree(node_id: NodeId | str) -> int`
- `contains(node_id: NodeId | str) -> bool`
- `size() -> int`
