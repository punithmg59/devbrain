# Cost Model Subsystem Architecture

## Overview
The Cost Model (`graph_query_engine.cost`) provides a deterministic, explainable, execution-independent analysis pass that assigns cost estimates to a `LogicalPlan`.

Modeled after PostgreSQL's cost estimator, Apache Calcite's `RelMetadataQuery`, Neo4j planner statistics, and LLVM analysis passes, this subsystem estimates work without executing query operations.

---

## Architectural Guarantees

```
                     +---------------------------------------+
                     |              LogicalPlan              |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |             CostEstimator             |
                     +---------------------------------------+
                      /          |             |           \
                     /           |             |            \
        SelectivityEst   CardinalityEst   ResourceEst    CostAggregator
```

1. **Zero Execution**: Does NOT execute graph traversals or queries.
2. **Zero Plan Mutation**: Does NOT modify the `LogicalPlan` tree.
3. **Zero GraphView Access**: Does NOT touch `GraphView` or storage layers.
4. **100% Immutability**: All estimates, reports, statistics, and breakdowns are frozen Pydantic models.
5. **Deterministic**: Given identical `LogicalPlan` and `GraphStatisticsMetadata`, yields identical cost estimates.
