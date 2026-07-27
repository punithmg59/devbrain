# Traversal Metrics

## Overview

`TraversalMetrics` is an immutable metrics container recording execution impact:

- `nodes_visited`: Count of unique nodes visited.
- `edges_visited`: Count of edges traversed.
- `paths_explored`: Count of paths discovered.
- `max_depth`: Deepest level reached.
- `average_branching_factor`: Average out-degree of explored nodes.
- `execution_duration_ms`: Duration in milliseconds.
- `cache_hits` & `cache_misses`: Index lookup performance.
- `algorithm_usage`: Execution counts per algorithm.
- `operator_counts`: Execution counts per operator.
