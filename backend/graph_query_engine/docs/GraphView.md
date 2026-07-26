# GraphView Architectural Documentation

## Purpose
`GraphView` is the immutable, read-only, thread-safe graph snapshot abstraction for DevBrain's Graph Query Engine.

The rest of the Graph Query Engine (indexers, planners, traversal engines) NEVER interacts directly with raw repository data or mutates graph states. All query access is executed exclusively through `GraphView`.

---

## GraphIdentity Refinement
`GraphMetadata` delegates snapshot identity management to `GraphIdentity`, which encapsulates:
- `repository_id: RepositoryId`
- `snapshot_id: SnapshotId`
- `graph_version: str`
- `schema_version: str`
- `analyzer_version: str`
- `graph_hash: str`
- `language: LanguageId`

---

## Key Guarantees
1. **Immutability**: Once instantiated via `GraphViewFactory`, `GraphView` and its child views (`ImmutableNodeView`, `ImmutableEdgeView`, `GraphIdentity`, `GraphMetadata`, `GraphSnapshotInfo`, `GraphStatistics`) cannot be modified.
2. **Thread Safety**: Immutable mappings and tuples ensure zero data races across concurrent query worker threads.
3. **Determinism**: Identical graph inputs yield 100% deterministic neighbor and edge lookups.
4. **Contract Compliance**: Implements the public `IGraphView` protocol (`graph_query_engine.contracts.view`).

---

## Class Interfaces

```python
class GraphView(BaseModel):
    snapshot_id: SnapshotId
    repository_id: RepositoryId
    schema_version: str
    nodes: Mapping[NodeId, ImmutableNodeView]
    edges: Mapping[EdgeId, ImmutableEdgeView]
    metadata: GraphMetadata
    snapshot: GraphSnapshotInfo
    statistics: GraphStatistics

    def get_node_view(node_id: NodeId) -> Optional[ImmutableNodeView]
    def get_edge_view(edge_id: EdgeId) -> Optional[ImmutableEdgeView]
    def get_neighbors(node_id: NodeId, relationship_type: Optional[RelationshipType] = None) -> Iterable[NodeId]
```
