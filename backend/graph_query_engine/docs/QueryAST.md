# Query AST Node Hierarchy

## Overview
`QueryASTNode` provides a composite tree structure for representing query logic in a strongly-typed, immutable hierarchy.

---

## Node Classifications (`ASTNodeType`)
- `OPERATOR`: Wraps a declarative `QueryOperator` (Lookup, Expand, Impact, Path, Filter, etc.).
- `EXPRESSION`: Wraps a `QueryExpression` (Literal, PropertyAccess, Comparison, Logical, etc.).
- `PREDICATE`: Wraps a `QueryPredicate` (And, Or, Not, Equality, Range, Node, etc.).
- `REFERENCE`: Wraps an `EntityReference` (Symbol, File, Package, Class, Function, etc.).

---

## Key AST Capabilities
1. **Visitor Traversal**: Dispatches `node.accept(visitor)` for extensible tree walking.
2. **Self-Validation**: `node.validate_node()` returns structural errors.
3. **Serialization**: `node.to_dict()` serializes node trees cleanly.
