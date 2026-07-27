# Physical Planner Component Specification

## Overview
The Physical Planner (`graph_query_engine.physical`) translates a `LogicalPlan` and `CostReport` into an execution-independent `PhysicalPlan`.

Like PostgreSQL's physical path selector, Neo4j's physical execution planner, Apache Calcite's physical converter, and LLVM instruction selection, it decides **HOW** the query should be executed without ever performing actual execution or accessing `GraphView`.

---

## Workflow Sequence

1. Consumes a validated `LogicalPlan` and `CostReport`.
2. Recursively walks `LogicalPlanNode` tree.
3. Invokes strategy selectors (`LookupStrategySelector`, `ExpandStrategySelector`, `JoinStrategySelector`, `PushdownStrategySelector`).
4. Constructs `PhysicalPlanNode` tree wrapping selected physical operators (`IndexLookup`, `BreadthExpand`, `HashJoin`, `FilterPushdown`, etc.).
5. Validates physical tree invariants using `PhysicalPlanValidator`.
6. Collects strategy choice rationale in `PhysicalPlannerDiagnostics`.
7. Returns the canonical, immutable `PhysicalPlan`.
