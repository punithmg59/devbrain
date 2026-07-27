# Cost Statistics Layer Specification

## Overview
The Statistics Layer provides population metrics and index availability hints used during cost estimation.

---

## Models
- `NodeStatistics`: Node population count and node type distribution.
- `EdgeStatistics`: Edge count, average degree, min/max degrees, and relationship type counts.
- `IndexStatisticsMetadata`: Available index names and selectivity hints.
- `GraphStatisticsMetadata`: Combined graph statistics container.
- `RepositoryStatisticsMetadata`: Repository-level statistics wrapper.
