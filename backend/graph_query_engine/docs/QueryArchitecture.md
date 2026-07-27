# Query Representation Layer Architecture

## Overview
The Query Representation Layer (`graph_query_engine.query`) defines the canonical, compiler-grade, language-neutral, and 100% immutable representation of engineering queries within DevBrain.

Similar to LLVM IR, Roslyn AST, Apache Calcite `RelNode` trees, PostgreSQL `QueryTree`, and IntelliJ PSI, this layer serves as the intermediate representation (IR) language of the query planner.

---

## Architectural Isolation Guarantees

```
                     +---------------------------------------+
                     |         EngineeringQuery Model        |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |           Query AST Root              |
                     +---------------------------------------+
                      /          |             |           \
                     /           |             |            \
       QueryOperator   QueryExpression   QueryPredicate  EntityReference
```

1. **Zero Execution**: This layer does NOT execute queries or graph algorithms.
2. **Zero Graph Access**: It contains NO references to `GraphView` or internal graph storage formats.
3. **Zero Index Access**: It does NOT perform index lookups or semantic resolution.
4. **Zero Planning/Optimization**: It performs no plan generation or rule optimization (those are handled by Step 4.3 Logical Planner).
5. **100% Immutability**: All AST nodes, models, constraints, result specs, and references are frozen Pydantic models.

---

## Package Subsystems

| Module | Description | Key Components |
| :--- | :--- | :--- |
| `query.version` | Schema & AST versioning | `QueryVersion`, `VersionMigrationRegistry` |
| `query.diagnostics` | Location tracking & diagnostics | `SourceLocation`, `QueryDiagnosticItem` |
| `query.references` | Strongly typed entity references | `SymbolReference`, `FileReference`, `PackageReference` |
| `query.expressions` | Expression AST nodes | `LiteralExpression`, `ComparisonExpression` |
| `query.predicates` | Filter predicate AST nodes | `AndPredicate`, `EqualityPredicate`, `NodePredicate` |
| `query.traversal` | Traversal request specifications | `TraversalRequest`, `TraversalConstraint` |
| `query.operators` | Declarative query operators | `LookupOperator`, `ExpandOperator`, `ImpactOperator` |
| `query.constraints` | Resource budget constraints | `QueryConstraints`, `TimeBudgetConstraint` |
| `query.result` | Result shaping specifications | `ResultSpecification`, `ResultProjection` |
| `query.ast` | AST tree composite nodes | `QueryASTNode`, `QueryAST`, `ASTNodeType` |
| `query.model` | Canonical query root model | `EngineeringQuery`, `QueryMetadata` |
| `query.visitor` | Visitor pattern traversal | `QueryVisitor`, `BaseQueryVisitor`, `PrintVisitor` |
| `query.validation` | Structural AST validator | `QueryValidator`, `ValidationReport` |
| `query.builder` | Fluent immutable builders | `QueryBuilder`, `ASTBuilder` |
| `query.serialization` | Serializers (JSON/YAML/Binary) | `JSONQuerySerializer`, `YAMLQuerySerializer` |
