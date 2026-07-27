# Traversal Diagnostics & Telemetry

## Overview

`TraversalDiagnostics` provides thread-safe telemetry recording for graph traversal runs.

It records:
- Information entries (`record_info`)
- Warning entries (`record_warning`) for cycles, depth cutoffs, and limit warnings
- Error entries (`record_error`) for failures
- Algorithm tracking (`set_algorithm`)
- Pruning statistics (`record_pruning`)
- Index cache hits and misses (`record_cache_hit`, `record_cache_miss`)
