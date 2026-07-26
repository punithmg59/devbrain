# ADR 0002: Deterministic Access over Immutable Graph Snapshots

## Context
DevBrain produces immutable graph segment snapshots during repository analysis. The Graph Query Engine acts exclusively as a read-only deterministic access layer over these snapshots.

## Decision
- The Graph Query Engine shall NOT modify, write, or mutate graph storage.
- All query executions against a specific `SnapshotId` must return 100% deterministic, repeatable results.
- Data structures passed through the engine (`NodeId`, `EdgeId`, `GraphQueryEngineConfig`, `Result`, `Option`) must be immutable (`frozen=True` dataclasses, Pydantic frozen models, or NewTypes).

## Consequences
- **Positive**: Eliminates data corruption, race conditions, and side-effects during concurrent query execution. Enables aggressive caching of query plans and results.
- **Negative**: Dynamic mutations or graph editing require generating a new immutable snapshot upstream.

## Alternatives Considered
- **In-Memory Mutable Graph**: High risk of state corruption during parallel change impact analyses.

## Future Impact
Ensures reproducible change intelligence reports and thread-safe parallel traversal execution.
