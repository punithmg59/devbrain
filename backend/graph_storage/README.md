# Graph Storage Module

Production-ready modular architecture for DevBrain Graph Storage.

## Package Architecture & Boundaries

- `config/`: System configuration and storage parameters (Leaf layer).
- `exceptions/`: Domain exception hierarchy for storage errors (Leaf layer).
- `model/`: Storage-domain models only (`SnapshotMetadata`, `VersionRef`, `ManifestEntry`, `SegmentDescriptor`, `StorageStatistics`, `StorageHealth`, `ArtifactMetadata`).
- `serialization/`: Binary serialization, data encoding/decoding, format codecs, and schema versioning (Core layer).
- `validation/`: Schema enforcement, structural constraints, and storage validation rules (Core layer).
- `manifest/`: Snapshot catalog, version references, manifest log, and manifest index (Core layer).
- `partitioning/`: Storage partitioning strategies, segment allocation policies, and partition mapping (Core layer).
- `backend/`: Storage backend drivers and implementations (`LocalFileBackend`, `MemoryBackend`, `S3Backend`) (Infrastructure layer).
- `segment/`: `SegmentReader`, `SegmentWriter`, segment metadata, and segment lifecycle management (Infrastructure layer).
- `cache/`: Storage segment caching, eviction policies, memory budget management, and cache stats (Infrastructure layer).
- `transaction/`: Storage transaction boundaries (`ReadTransaction`, `WriteTransaction`, `TransactionArbiter`, `WriteIntentLog`, lease management) (Infrastructure layer).
- `diagnostics/`: Storage health reporting, integrity verification, operational state, and diagnostic reports (Operations layer).
- `metrics/`: Storage operational metrics (read/write latency, cache hit ratio, storage size, segment count) (Operations layer).
- `api/`: Public API entry points and client boundary contracts (Public API layer).

## Architectural Layering

```
[Public API]     api
                  │
[Operations]     diagnostics ─── metrics
                  │
[Infrastructure] backend ── segment ── cache ── transaction
                  │
[Core]           serialization ── validation ── manifest ── partitioning
                  │
[Leaf]           config ── exceptions ── model
```
