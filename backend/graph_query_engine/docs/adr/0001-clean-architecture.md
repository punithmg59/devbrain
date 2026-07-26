# ADR 0001: Adoption of Clean Architecture and Layered Boundaries

## Context
DevBrain requires an enterprise-grade deterministic Graph Query Engine capable of serving complex structural queries over code repositories. The system must remain maintainable, testable, and stable for a 10-year operational horizon.

## Decision
We adopt Clean Architecture principles for the Graph Query Engine:
- Infrastructure and domain abstractions (`types`, `errors`, `config`, `contracts`) form the inner layers.
- Query planning, traversal strategies, secondary indexing, and execution pipelines depend only on inner interfaces via Protocols (`typing.Protocol`).
- Dependency Injection (DI) is strictly contract-based (`ServiceRegistry`, `ComponentProvider`) without singletons or global mutable state.

## Consequences
- **Positive**: Components are decoupled, fully unit-testable in isolation, and easily mockable.
- **Negative**: Requires strict protocol definitions and discipline in importing contracts rather than concrete implementations.

## Alternatives Considered
- **Monolithic Single Package**: Simple initially, but leads to tight coupling, circular imports, and high regression risks.
- **Classic 3-Tier Architecture**: Insufficiently granular for compiler-grade graph query planning and execution pipelines.

## Future Impact
Sustains seamless extensibility as GraphView adapters, deterministic planners, and graph traversal engines are introduced in Step 2+.
