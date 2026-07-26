# ADR 0003: Package Encapsulation and Internal Package Privacy

## Context
As the engine grows, internal implementation details (planners, caches, optimizations) must remain private to prevent downstream modules from taking hard dependencies on transient internals.

## Decision
- We create `graph_query_engine.internal` as a private root package containing all internal execution sub-modules (`planner`, `traversal`, `pipeline`, `cache`, `optimization`, `validation`).
- Code in `graph_query_engine.internal` MUST NEVER be imported by external packages.
- Every package in `graph_query_engine` MUST define an explicit `__all__` export list in its `__init__.py`.

## Consequences
- **Positive**: Guarantees zero leakage of internal implementation details. Downstream code depends strictly on public contracts.
- **Negative**: Requires explicit public export management via `__all__`.

## Alternatives Considered
- **Single Public Flat Package**: Exposes all internal classes to consumers, leading to high breaking-change risk.

## Future Impact
Allows internal algorithms (BFS/DFS optimizations, memory caches) to be refactored without breaking external API contracts.
