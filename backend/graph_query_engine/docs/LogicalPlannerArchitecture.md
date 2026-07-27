# Logical Planner Architecture

## Overview
The Logical Planner layer (`graph_query_engine.logical`) translates validated `EngineeringQuery` AST models into an intermediate, execution-independent `LogicalPlan`.

The Logical Planner answers only one fundamental question:
> **"What work needs to be performed?"**

It NEVER answers *"How should it be executed?"* (Physical planning, index selection, cost estimation, and graph algorithms belong to subsequent pipeline steps).

---

## Architectural Position

```
                     +---------------------------------------+
                     |           EngineeringQuery            |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |            LogicalPlanner             |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |          ASTLoweringPipeline          |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |         LogicalPlanValidator          |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |              LogicalPlan              |
                     +---------------------------------------+
```

---

## Key Principles & Guarantees

1. **Execution Independence**: The resulting `LogicalPlan` contains no physical execution hints, thread dispatch settings, or storage format specifics.
2. **Zero GraphView/Index Access**: The Logical Planner does NOT query `GraphView`, index structures, or physical caches.
3. **Immutability**: All operators, nodes, metadata, and plans are 100% frozen Pydantic models.
4. **Deterministic Lowering**: Every AST node type has a deterministic AST lowering rule.
5. **Visitor Pattern Integration**: Supports AST walking for serialization, printing, structural validation, and future optimization passes.
