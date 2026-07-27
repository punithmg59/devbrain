# Query Expressions & Predicates Specification

## Overview
Query Expressions and Predicates define the scalar evaluation logic and boolean filtering conditions embedded within Query ASTs.

---

## Expressions (`QueryExpression`)
- `LiteralExpression`: Constant values (string, int, float, bool).
- `PropertyAccessExpression`: Attribute reference (e.g. `node.name`).
- `ComparisonExpression`: Binary comparisons (`=`, `!=`, `<`, `<=`, `>`, `>=`).
- `LogicalExpression`: Logical composition (`AND`, `OR`, `NOT`).
- `ArithmeticExpression`: Arithmetic operations (`+`, `-`, `*`, `/`).
- `CollectionExpression`: Collection membership (`IN`, `CONTAINS_ANY`, `CONTAINS_ALL`).
- `BooleanExpression` & `NullExpression`: Constant boolean/null.

---

## Predicates (`QueryPredicate`)
- Logical composition: `AndPredicate`, `OrPredicate`, `NotPredicate`.
- Value filtering: `EqualityPredicate`, `RangePredicate`, `ContainsPredicate`, `StartsWithPredicate`, `EndsWithPredicate`, `ExistsPredicate`.
- Entity filtering: `RelationshipPredicate`, `NodePredicate`, `AttributePredicate`.
