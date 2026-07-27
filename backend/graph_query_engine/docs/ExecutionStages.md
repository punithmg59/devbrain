# Execution Stages & Pipeline Specification

## Overview
`ExecutionStage` objects partition physical operator trees into independently executable units with explicit dependency bounds.

---

## Supported Stage Types
- `LOOKUP`: Index or sequential table lookup.
- `FILTER`: Predicate filter evaluation.
- `EXPANSION`: Graph edge expansion traversal.
- `PROJECTION`: Field projection trimming.
- `JOIN`: Hash, merge, or nested loop join.
- `AGGREGATION`: Stream/hash aggregation.
- `SORTING`: In-memory sorting.
- `DEDUPLICATION`: Distinct deduplication.
- `LIMIT`: Pagination limit/offset.
