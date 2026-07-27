# AST → Logical Plan Lowering Rules

## Overview
`ASTLoweringPipeline` uses rule-based AST node transformations to build logical plan operator trees.

---

## Lowering Rules Matrix

| Query AST Node | Logical Operator | Rule Class |
| :--- | :--- | :--- |
| `LookupOperator` | `LogicalLookupOperator` | `LookupLoweringRule` |
| `ExpandOperator` | `LogicalExpandOperator` | `ExpandLoweringRule` |
| `FilterOperator` | `LogicalFilterOperator` | `FilterLoweringRule` |
| `ProjectionOperator` | `LogicalProjectionOperator` | `ProjectionLoweringRule` |
| `AggregateOperator` | `LogicalAggregateOperator` | `AggregateLoweringRule` |
| `GroupingOperator` | `LogicalGroupingOperator` | `GroupingLoweringRule` |
| `SortingOperator` | `LogicalSortingOperator` | `SortingLoweringRule` |
| `DeduplicationOperator` | `LogicalDeduplicationOperator` | `DeduplicationLoweringRule` |
| `LimitOperator` | `LogicalLimitOperator` | `LimitLoweringRule` |
| `JoinOperator` | `LogicalJoinOperator` | `JoinLoweringRule` |
