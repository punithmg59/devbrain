# Execution Planner Subsystem Architecture

## Overview
The Execution Planner (`graph_query_engine.execution`) decomposes a `PhysicalPlan` into an independently executable, stage-based `ExecutionPlan`.

Modeled after PostgreSQL's executor plan, Apache Calcite's executable stage graph, LLVM lowering passes, Spark execution plans, and Neo4j runtime plans, it completely describes **HOW** the runtime will execute the query without ever performing actual runtime execution or accessing `GraphView`.

---

## Workflow Sequence

1. Consumes an immutable `PhysicalPlan`.
2. Recursively walks `PhysicalPlanNode` tree.
3. Partitions physical operators into independently executable `ExecutionStage` objects (`LookupStage`, `FilterStage`, `ExpansionStage`, `AggregationStage`, `SortingStage`, `ProjectionStage`, `JoinStage`, `DeduplicationStage`, `LimitStage`).
4. Converts physical operators into `ExecutionOperator` wrappers.
5. Constructs `StageDependencyGraph` (DAG topology) and topological execution order.
6. Allocates runtime `ExecutionMetadata` (timeout, memory limit, cancellation token ID, progress handle ID).
7. Validates DAG acyclicity and stage dependencies using `ExecutionPlanValidator`.
8. Returns the canonical, immutable `ExecutionPlan`.
