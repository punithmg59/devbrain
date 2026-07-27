# Declarative Query Operators Specification

## Overview
Query Operators represent structural operations requested by engineering queries without executing planning algorithms or accessing underlying graph views.

---

## Supported Operators

1. **`LookupOperator`**: Direct lookup of entity references.
2. **`ExpandOperator`**: Declarative graph relationship expansion.
3. **`ImpactOperator`**: Downstream/upstream change impact analysis specification.
4. **`ReachabilityOperator`**: Path reachability query spec between entities.
5. **`UsageSearchOperator`**: Symbol/entity caller reference search spec.
6. **`HierarchyOperator`**: Inheritance or type hierarchy navigation spec.
7. **`PathOperator`**: Shortest or all-paths query specification.
8. **`AggregateOperator`**: Aggregation specification (COUNT, SUM, AVG, MIN, MAX).
9. **`ProjectionOperator`**: Field projection selection.
10. **`GroupingOperator`**: Group-by field specification.
11. **`SortingOperator`**: Order-By field specification.
12. **`DeduplicationOperator`**: Distinct deduplication spec.
13. **`LimitOperator`**: Offset and limit pagination spec.
14. **`FilterOperator`**: Predicate filtering operator.
15. **`JoinOperator`**: Logical join operator combining query branches.
