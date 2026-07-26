# ADR 0005: Public API Freeze and Interface Stabilization

## Context
Downstream components in DevBrain (Blast Radius Engine, Change Intelligence Platform) rely on a stable API contract for query execution.

## Decision
- All public contract interfaces (`IGraphView`, `IQueryPipeline`, `IQueryPlanner`, `ITraversalStrategy`, `IQueryContext`, `IQueryEngineAPI`, etc.) are unified under `graph_query_engine.contracts` and frozen.
- No public interface signatures may be altered without semantic versioning major increments.

## Consequences
- **Positive**: Complete stability for downstream DevBrain modules.
- **Negative**: Requires careful design when adding new parameter contracts.

## Alternatives Considered
- **Unfrozen Dynamic APIs**: Causes breaking changes across backend microservices.

## Future Impact
Enables parallel development of upstream AI change intelligence engines while query engine implementation matures.
