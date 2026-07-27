# Query Visitor Pattern Specification

## Overview
The Visitor Pattern (`graph_query_engine.query.visitor`) provides the primary mechanism for future subsystems (Logical Planner, Optimizer, Diagnostics, Serializer, Validator) to inspect and transform Query ASTs without mutating AST node structures.

---

## Infrastructure Classes

1. **`QueryVisitor`**: Protocol defining required visitor methods.
2. **`BaseQueryVisitor`**: Default depth-first AST tree walker.
3. **`PrintVisitor`**: Renders human-readable formatted AST text trees.
4. **`ValidationVisitor`**: Traverses AST trees to aggregate structural validation error messages.

---

## Usage Example
```python
visitor = PrintVisitor()
formatted_tree = visitor.print_tree(query)
print(formatted_tree)
```
