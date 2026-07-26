# GraphAdapter Architectural Documentation

## Purpose
`GraphAdapter` is a stateless, pure read-only transformer that converts DevBrain's `DependencyGraph` model into an immutable `GraphView`.

---

## Strict Behavioral Boundaries
- **NO State Storage**: `GraphAdapter` does not hold references to transformed graphs.
- **NO Mutations**: `GraphAdapter` never modifies input `DependencyGraph` objects.
- **NO Query Execution / Traversal**: Performs pure model translation only.
- **NO Index Building**: Indexes are handled strictly in Step 3.

---

## Usage Example

```python
from graph_query_engine.adapter import GraphAdapter

# Adapt DependencyGraph model into GraphView
graph_view = GraphAdapter.adapt(dependency_graph)

# Access node views deterministically
node_view = graph_view.get_node_view(NodeId("sym_123"))
```
