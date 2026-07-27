# Physical Operators Specification

## Overview
Physical operators represent concrete physical execution strategies and algorithms.

---

## Supported Operators
- `IndexLookupPhysicalOperator`: Point/range index lookup.
- `SequentialLookupPhysicalOperator`: Full scan fallback lookup.
- `BreadthExpandPhysicalOperator`: Breadth-First Search (BFS) graph expansion.
- `DepthExpandPhysicalOperator`: Depth-First Search (DFS) graph expansion.
- `BidirectionalExpandPhysicalOperator`: Bidirectional search expansion.
- `PathExpandPhysicalOperator`: Path search expansion.
- `HierarchyExpandPhysicalOperator`: Symbol hierarchy expansion.
- `FilterPushdownPhysicalOperator`: Pushed-down filter predicate evaluation.
- `ProjectionPushdownPhysicalOperator`: Pushed-down field projection.
- `HashJoinPhysicalOperator`: In-memory hash join.
- `NestedLoopJoinPhysicalOperator`: Nested loop join.
- `MergeJoinPhysicalOperator`: Sorted merge join.
- `AggregationExecutionPhysicalOperator`: Physical aggregation.
- `SortingExecutionPhysicalOperator`: Physical sorting.
- `DeduplicationExecutionPhysicalOperator`: Physical distinct deduplication.
- `LimitExecutionPhysicalOperator`: Physical pagination limit/offset.
